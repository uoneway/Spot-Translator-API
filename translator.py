import re
import requests
import fasttext
# from pororo import Pororo  
from utils import load_obj


BASE_URL = "https://openapi.naver.com/v1/papago/n2mt"

PAPAGO_CAN_LANG = {  # https://developers.naver.com/docs/papago/papago-nmt-api-reference.md
        'ko': ('en', 'ja', 'zh-CN', 'zh-TW', 'vi', 'id', 'th', 'de', 'ru', 'es', 'it', 'fr'),
        'en': ('ko', 'ja', 'zh-CN', 'zh-TW', 'fr'),
        'ja': ('ko', 'en', 'zh-CN', 'zh-TW'),
        'zh-CN': ('ko', 'en', 'ja', 'zh-TW'),  # 중국어 간체
        'zh-TW': ('ko', 'en', 'ja', 'zh-CN'),  # 중국어 번체
}
# PORORO_CAN_LANG = {  # https://kakaobrain.github.io/pororo/seq2seq/mt.html
#     'ko': ('en', 'ja', 'zh'),
#     'en': ('ko', 'ja', 'zh'),
#     'ja': ('ko', 'en', 'zh'),
#     'zh': ('ko', 'en', 'ja'),
# }
CAN_LANG = ('ko', 'en')

# print(Pororo.available_models("named_entity_recognition"))
# print("Start to load Pororo NER models...")
# ner_models = {
#     'ko': Pororo(task="ner", lang="ko"),
#     'en': Pororo(task="ner", lang="en"),
#     # 'ja': Pororo(task="ner", lang="ja"),
# }
# print("End to load Pororo NER models!")

BASE_TERM_SET_PATH = 'datasets/ml_term_set.pkl'
BASE_TERM_SET = load_obj(BASE_TERM_SET_PATH)
BASE_TERM_LIST = list(BASE_TERM_SET)
# special_to_original_dict = {idx: value for idx, value in enumerate(BASE_TERM_SET)}

## reg expression
#  2. 문장 중간에 대문자로 시작(전체 대문자인 경우도 포함)하거나 문장(또는 전체 string)처음이지만 전체가 대문자인 경우 
# UDF FasdFsada. Instead Unigram.[1] This Will. \n FasdFsada  에서 
# UDF, FasdFsada, Unigram, Will, FasdFsada 등은 선택하고 Instead, This는 제외
REG_FIND_CAPITAL_PREFIX = re.compile(r"((?<=[^\\]\w )[A-Z][\d\w]*)|((?<=(?<=\A)|(?<=\n))([A-Z]+[a-z]*){2,}(?=\s))")


def identify_lang(text):
    max_char_num = 100
    max_token_num = 20
    if len(text) > max_char_num:
        text = text.split()[:max_token_num]

    lang_detect_model = fasttext.load_model('models/fasttext_lid.176.ftz')
    result = lang_detect_model.predict(text) #  k=2,  # '__label__en'
    lang = result[0][0].split('__')[-1]

    return lang


def isKoreanIncluded(text, check_to_num=-1):
    """
    Check whether the text have korean unicode or not
    https://arisri.tistory.com/267
    """
    check_to_num = min(len(text)-1, check_to_num)

    for i in text[:check_to_num]:
        if ord(i) > int('0x1100',16) and ord(i) < int('0x11ff',16) \
            or ord(i) > int('0x3131',16) and ord(i) < int('0x318e',16) \
            or ord(i) > int('0xa960',16) and ord(i) < int('0xa97c',16) \
            or ord(i) > int('0xac00',16) and ord(i) < int('0xd7a3',16) \
            or ord(i) > int('0xd7b0',16) and ord(i) < int('0xd7fb',16):
                return True

    return False


def _replace_ne_to_special_token(text, source_lang, predefiend_ne_set: set=None):

    # 시도1:처음에는 ner 단어를 활용해서 대치하려고 했으나 
    # 어떤 경우에는 그 기호 안에 있는 ner도 해석해버리는 경우가 많고, 다른 단어 해석에도 영향을 미칠 수 있음에 따라
    # 시도2: 'NER1'과 같이 보통 문장 쓸 떄도 키워드를 지칭해주는 방식으로 바꿔주고 + 의미없는 NER을 붙여줘서 바꿔주고
    #  추후다시 대치하는 방식으로 사용
    # 근데 다시 여러가지 실험하다 보니 해당 단어를 지우고 '[1]'이나 '[NE1]', '[N1E]', 그냥 단어 양옆에 '' 넣어주는 등으로 대체하는게 아래 같은 텍스트 번역을 이상하게 만듦
    #     Gunicorn forks multiple system processes within each dyno to allow a Python app to support multiple concurrent requests without requiring them to be thread-safe. In Gunicorn terminology, these are referred to as worker processes (not to be confused with Heroku worker processes, which run in their own dynos).
    # 이건 계속 그대로인 예제: Then you will add the following line in your Procfile
    # 시도3: 그래서 
    # 영어는 그냥 단어를 모두 대문자로 바꿨다가 원복해주는 방식으로. 한국어는 해당 문자에 '' 붙여줬다가 복원
    # 참고: 중요한 부분을 두드러지게 할 때 https://thoughts.chkwon.net/punctuation-korean-english/
    # 한글에서는 ‘드러냄표’ 혹은 ‘밑줄’을 사용하는 것을 기본으로 ‘작은따옴표’의 사용도 허락한다.
    # - 영어에서는 italics(이탤릭체)를 주로 사용하며, 때에 따라서 boldface(굵은 글씨체), underline(밑줄) 등을 사용하기도 한다. 
    # 어떤 이는 single quotation mark(작은 따옴표) 혹은 double quotation mark(큰 따옴표)를 사용하기도 하나, 일반적으로 잘못된 용법이라고 한다.
    # 시도4: 트위터 태그를 활용한 @TAG1 방식으로.

    # ner_set = set()
    # for ner_tuple in ner_results:
    #     if ner_tuple[1] != 'O':  # NER
    #         ner_set.add(ner_tuple[0])
    # joined_ner = '|'.join(ner_set)
    # prep_text = re.sub(f'(\W|^)({joined_ner})(\W|$)', r'\1[/\2/]\3', text)
    
    detected_ne_set = set()

    # 대치한 경우를 모두 dict에 담아줘서 추후 다시 복구하는게 안전할 것 같지만...  replaced_dict = {}

    #1. ne detection model 사용
    # ner_model = ner_models[lang]
    # ner_results = ner_model(text)

    # for ner_tuple in ner_results:  
    #     if ner_tuple[1] != 'O':
    #         # print(ner_tuple[0])
    #         detected_ne_set.add(ner_tuple[0])
    # print("1. Detected NEs: ", detected_ne_set)

    # 2. 문장 중간에 대문자로 시작(전체 대문자인 경우도 포함)하거나 문장(또는 전체 string)처음이지만 전체가 대문자인 경우 
    match_objs = re.finditer(REG_FIND_CAPITAL_PREFIX, text) 
    capital_prefix_token_set = {match_obj.group() for match_obj in match_objs}

    print("2. Detected Capital tokens: ", capital_prefix_token_set)
    detected_ne_set.update(capital_prefix_token_set)

    # 3. predefiend_ne_set을 대소문자 구분없이 일치하는 token 찾아내기
    predefiend_detected_ne_set = set()
    if predefiend_ne_set is not None:
        # start_idx = len(detected_ne_list)
        for predefiend_ne in predefiend_ne_set:
            from_reg = re.compile(f'(?<=(?<=\s)|(?<=\A)){predefiend_ne}(?=(?=\W)|(?=\Z))', re.IGNORECASE)
            match_objs = re.finditer(from_reg, text) 
            predefiend_detected_ne_set.update({match_obj.group() for match_obj in match_objs})

        
            # to_reg = rf"'NE{idx+}'"

            # text = re.sub(from_reg, to_reg, text)
    print("3. Detected from predefiend_ne_set: ", predefiend_detected_ne_set)
    detected_ne_set.update(predefiend_detected_ne_set)


    # 1+2+3 대치. 사용자가 넣은 문장 안에서 찾은 결과이기 때문에 찾은것 그대로만(대소문자 구분 등) 찾아서 대치
    # 물론 해당 자리의 단어가 아닌 다른 자리 단어또한 대치될 위험성도 존재하나...
    print("Before: ", text)
    detected_ne_list = list(detected_ne_set)
    for idx, ne in enumerate(detected_ne_list):
        # print(term)
        # 앞에 무조건 공백이나 문장시작. 뒤에는 단어만 아니면 공백이나 기호도 올수 있음(그 기호는 그대로 놔둠)
        # 예시문장:  data  .data.  SS-data df data  sf-data-sdf data.
        # data data data. 는 대치. .data. SS-data sf-data-sdf 등은 대치하지 않음 
        from_reg = re.compile(f'(?<=(?<=\s)|(?<=\A)){ne}(?=(?=\W)|(?=\Z))')  
        # to_str = f"{ne.upper()}" if source_lang == 'en' \
        #         else f"'{ne}'" # ko 경우.       f"'[{idx}]'"
        to_str = f"@TAG{idx}"

        text = re.sub(from_reg, to_str, text)
    print("After 1,2,3: ", text)


    return text, detected_ne_list

def _restore_ne(translated_text, source_lang, ne_list: list):
    # re.sub(r"'(NER)(\d+)'", rf"{ne_list[\2]}", translated_text)  # 변수 안에 reg ㅍ현이 들어가야 하는데 어떻게 하느거지..
    # if source_lang == 'en':
    #     for idx, ne in enumerate(ne_list):
    #         translated_text = translated_text.replace(ne.upper(), ne)

    # elif source_lang == 'ko':
    #     for idx, ne in enumerate(ne_list):
    #         translated_text = re.sub(rf"'{ne}'", ne, translated_text)   #rf"'\[{idx}\]'"    
    # else:
    #     print("error")

    for idx, ne in enumerate(ne_list):
        translated_text = translated_text.replace(f"@TAG{idx}", ne)

    return translated_text


def request_translate(source_text, source_lang, target_lang, api_client_id, api_client_secret):    
    data = {'text' : source_text,
            'source' : source_lang,
            'target': target_lang}

    header = {
        # 'content-type': 'application/json; charset=UTF-8',
        'X-Naver-Client-Id': api_client_id,
        'X-Naver-Client-Secret': api_client_secret
    }
    print(data)
    print(header)

    response = requests.post(BASE_URL, headers=header, data= data)
    rescode = response.status_code

    if(rescode==200):
        t_data = response.json()
        translated_text = t_data['message']['result']['translatedText']
        
        return translated_text, rescode

    else:
        print("Error Code:" , rescode)
        return None, rescode


def translate(source_text:str, api_client_id:str, api_client_secret:str,\
            main_lang:str='ko', sub_lang:str='en', term_set: set=None): 
    """
    main_lang: 사용자는 원문 클릭 시, 번역되어 보이는 언어(target language).
        단 source_text가 main_lang인 경우는 아래 sub_lang이 target language으로 역할)
    sub_lang: source_text가 main_lang인 경우 target language
    """

    # Check language of source_text
    source_lang = 'ko' if isKoreanIncluded(source_text, 100) else 'en'  # 추후 수정 필요. identify_lang(text)
    if source_lang not in CAN_LANG:
        raise ValueError

    target_lang = sub_lang if source_lang is main_lang else main_lang

    print("source_text:", source_text)
    
    if source_lang == 'en':
        term_set =  BASE_TERM_SET if term_set is None \
                    else (BASE_TERM_SET | term_set)
        prep_source_text, ners = _replace_ne_to_special_token(source_text, source_lang, term_set)
        print("prep_source_text:", prep_source_text)
    else:
        prep_source_text = source_text

    translated_text, rescode = request_translate(prep_source_text, source_lang, target_lang, api_client_id, api_client_secret)
    print("translated_text:", translated_text)

    if translated_text is None:
        return None, rescode
    else:
        result_text = _restore_ne(translated_text, source_lang, ners) if source_lang == 'en'\
            else translated_text
        print("result_text:", result_text)
        return result_text, rescode


if __name__ == '__main__':
    api_client_id = "PwtsQmgHn5h50GCthwtj"
    api_client_secret = "zNWtEXWpt_"

    # user_term_set_path = 'datasets/ml_term_set.pkl'
    # user_term_set = load_obj(user_term_set_path)

    text_ko = '오늘은 이상한 날이다' 
    text = 'Today is a strange day.' 

    print(translate(text, api_client_id, api_client_secret))
