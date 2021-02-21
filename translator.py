import fasttext  # pip install fasttext


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


if __name__ == '__main__':
    client_id = "PwtsQmgHn5h50GCthwtj"
    client_secret = "zNWtEXWpt_"
    text_ko = '오늘은 이상한 날이다' 
    text_en = 'Today is a strange day.' 
    target_lang = 'ko'

    source_lang = 'ko' if isKoreanIncluded(text_ko, 100) else 'en'  #identify_lang(text)
    if source_lang not in CAN_LANG:
        raise ValueError
    
    # prep_source_text, ners = replace_ner_to_special_token(text, source_lang)
    # translated_text = translate(prep_source_text, source_lang, target_lang, client_id, client_secret)
    # result_text = restore_ner(translated_text, ners)

    print(source_lang)
