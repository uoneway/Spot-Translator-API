import re
import fasttext  # pip install fasttext
from pororo import Pororo  # pip install pororo


BASE_URL = "https://openapi.naver.com/v1/papago/n2mt"

PAPAGO_CAN_LANG = {  # https://developers.naver.com/docs/papago/papago-nmt-api-reference.md
        'ko': ('en', 'ja', 'zh-CN', 'zh-TW', 'vi', 'id', 'th', 'de', 'ru', 'es', 'it', 'fr'),
        'en': ('ko', 'ja', 'zh-CN', 'zh-TW', 'fr'),
        'ja': ('ko', 'en', 'zh-CN', 'zh-TW'),
        'zh-CN': ('ko', 'en', 'ja', 'zh-TW'),  # 중국어 간체
        'zh-TW': ('ko', 'en', 'ja', 'zh-CN'),  # 중국어 번체
}
PORORO_CAN_LANG = {  # https://kakaobrain.github.io/pororo/seq2seq/mt.html
    'ko': ('en', 'ja', 'zh'),
    'en': ('ko', 'ja', 'zh'),
    'ja': ('ko', 'en', 'zh'),
    'zh': ('ko', 'en', 'ja'),
}
CAN_LANG = ('ko', 'en')

# print(Pororo.available_models("named_entity_recognition"))
print("Start to load Pororo")
ner_models = {
    'ko': Pororo(task="ner", lang="ko"),
    'en': Pororo(task="ner", lang="en"),
    'ja': Pororo(task="ner", lang="ja"),
}
print("End to load Pororo")


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


def replace_ner_to_special_token(text, lang):
    ner_model = ner_models[lang]
    ner_results = ner_model(text)
    # print(ner_results)

    ## ner 단어를 활용해서 대치하려고 했으나 어떤 경우에는 그 기호 안에 있는 ner도 해석해버리는 경우가 많고, 다른 단어 해석에도 영향을 미칠 수 있음
    # ner_set = set()
    # for ner_tuple in ner_results:
    #     if ner_tuple[1] != 'O':  # NER
    #         ner_set.add(ner_tuple[0])
    # joined_ner = '|'.join(ner_set)
    # prep_text = re.sub(f'(\W|^)({joined_ner})(\W|$)', r'\1[/\2/]\3', text)

    ## 'NER1'과 같이 바꿔주고 다시 대치
    ners = []
    for ner_tuple in ner_results:
        if ner_tuple[1] != 'O':  # NER
            ners.append(ner_tuple[0])

    for idx, ner in enumerate(ners):
        text = re.sub(f'(\W|^)({ner})(\W|$)', rf"\1'NER{idx}'\3", text)
    # # ' '.join(tokens)
    # print(ners)

    return text, ners

def restore_ner(translated_text, ners):
    # re.sub(r"'(NER)(\d+)'", rf"{ners[\2]}", translated_text)  # 변수 안에 reg ㅍ현이 들어가야 하는데 어떻게 하느거지..
    for idx, ner in enumerate(ners):
        translated_text = re.sub(rf"'NER{idx}'", ner, translated_text)

    return translated_text


if __name__ == '__main__':
    client_id = "PwtsQmgHn5h50GCthwtj"
    client_secret = "zNWtEXWpt_"
    text_ko = '오늘은 이상한 날이다' 
    text = 'Today is a strange day.' 
    target_lang = 'ko'

    source_lang = 'ko' if isKoreanIncluded(text, 100) else 'en'  #identify_lang(text)
    if source_lang not in CAN_LANG:
        raise ValueError
    
    prep_source_text, ners = replace_ner_to_special_token(text, source_lang)
    print(prep_source_text)
    # translated_text = translate(prep_source_text, source_lang, target_lang, client_id, client_secret)
    result_text = restore_ner(prep_source_text, ners)

    print(result_text)
