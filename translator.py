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


def _replace_ne_to_special_token(text, lang, predefiend_ne_set: set=None):

    ## 처음에는 ner 단어를 활용해서 대치하려고 했으나 
    # 어떤 경우에는 그 기호 안에 있는 ner도 해석해버리는 경우가 많고, 다른 단어 해석에도 영향을 미칠 수 있음에 따라
    # 'NER1'과 같이 보통 문장 쓸 떄도 키워드를 지칭해주는 방식으로 바꿔주고 + 의미없는 NER을 붙여줘서 바꿔주고
    #  추후다시 대치하는 방식으로 사용
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
    # UDF FasdFsada. Instead Unigram. This Will. \n FasdFsada 에서 
    # UDF, FasdFsada, Unigram, Will, FasdFsada 등은 선택하고 Instead, This는 제외
    match_objs = re.finditer(r"((?<=[^.] )[A-Z][\d\w]*)|((?<=(?<=\A)|(?<=\n))([A-Z]+[a-z]*){2,}(?=\s))", text) 
    capital_prefix_token_set = {match_obj.group() for match_obj in match_objs}

    print("2. Detected Capital tokens: ", capital_prefix_token_set)
    detected_ne_set.update(capital_prefix_token_set)

    # 3. predefiend_ne_set을 대소문자 구분없이 일치하는 token 찾아내기
    predefiend_detected_ne_set = set()
    if predefiend_ne_set is not None:
        # start_idx = len(detected_ne_list)
        for ne in predefiend_ne_set:
            from_reg = re.compile(f'(?<=(?<=\s)|(?<=\A)){ne}(?=(?=\W)|(?=\Z))', re.IGNORECASE)
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
        to_reg = rf"'NE{idx}'"

        text = re.sub(from_reg, to_reg, text)
    print("After 1,2,3: ", text)


    return text, detected_ne_list

def _restore_ne(translated_text, ne_list: list):
    # re.sub(r"'(NER)(\d+)'", rf"{ne_list[\2]}", translated_text)  # 변수 안에 reg ㅍ현이 들어가야 하는데 어떻게 하느거지..
    for idx, ne in enumerate(ne_list):
        translated_text = re.sub(rf"'NE{idx}'", ne, translated_text)

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


def translate(source_text: str, target_lang: str, api_client_id: str, api_client_secret: str, term_set: set=None): 
    # Check language of source_text
    source_lang = 'ko' if isKoreanIncluded(source_text, 100) else 'en'  #identify_lang(text)
    if source_lang not in CAN_LANG:
        raise ValueError

    print("source_text: ", source_text)
    
    term_set =  BASE_TERM_SET if term_set is None \
                else (BASE_TERM_SET | term_set)
    prep_source_text, ners = _replace_ne_to_special_token(source_text, source_lang, term_set)
    print("prep_source_text: ", prep_source_text)

    translated_text, rescode = request_translate(prep_source_text, source_lang, target_lang, api_client_id, api_client_secret)
    if translated_text is None:
        return None, rescode
    else:
        result_text = _restore_ne(translated_text, ners)
        return result_text, rescode


if __name__ == '__main__':
    api_client_id = "PwtsQmgHn5h50GCthwtj"
    api_client_secret = "zNWtEXWpt_"
    text_ko = '오늘은 이상한 날이다' 
    text = 'Today is a strange day.' 
    target_lang = 'ko'
    # user_term_set_path = 'datasets/ml_term_set.pkl'
    # user_term_set = load_obj(user_term_set_path)
    print(translate(text, target_lang, api_client_id, api_client_secret))
