import re
import requests


BASE_URL = "https://openapi.naver.com/v1/papago/n2mt"


if __name__ == '__main__':
    client_id = "PwtsQmgHn5h50GCthwtj"
    client_secret = "zNWtEXWpt_"
    text = 'Today is a strange day.'  #'오늘은 이상한 날이다'
    target_lang = 'ko'

    source_lang = 'ko' if isKoreanIncluded(text, 100) else 'en'  #identify_lang(text)
    if source_lang not in CAN_LANG:
        raise ValueError
    
    prep_source_text, ners = replace_ner_to_special_token(text, source_lang)
    translated_text = translate(prep_source_text, source_lang, target_lang, client_id, client_secret)
    result_text = restore_ner(translated_text, ners)

    print(result_text)
