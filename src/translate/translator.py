import logging
import re

import requests

from src.common.base import __get_logger, gen_log_text

logger = __get_logger()


def get_last_char(token):
    for char in reversed(token):
        if char.isalpha():  # not char.isdigit():
            return char
    return "T"


class Translator:
    BASE_URL = "https://openapi.naver.com/v1/papago/n2mt"

    CAN_LANG = ("ko", "en")

    TO_BE_REMOVED_TERM_LIST = set(["I"])
    # special_to_original_dict = {idx: value for idx, value in enumerate(BASE_TERM_SET)}

    # REG_REPLACER
    # UDF FasdFsada. Instead Unigram.[1] This Will. \n FasdFsada sdf_csd _sdf WILL _sdf  에서
    # UDF, FasdFsada, Unigram, Will, FasdFsada 등은 선택하고 Instead, This는 제외
    REG_CAPITAL_PREFIX = r"((?<=[^\\]\w )([a-zA-Z0-9]*[-])*[A-Z][\d\w]*)([-][a-zA-Z0-9]*)*"  # 문장 중간에 대문자로 시작(전체 대문자인 경우도 포함) + 대문자단어와 -로 연결되어 있는 경우까지 포함
    REG_ALL_CAPITAL_AT_SENT_START = r"((?<=(?<=\A)|(?<=\n)|(?<=\.\s))([A-Z]+[a-z]*){2,}(?=\s))"  # 문장(또는 전체 string)처음이지만 전체가 대문자인 경우. 처음에 나오더라도 A와 같이 한 글자인 경우는 제외
    REG_HAVE_UNDERSCORE = r"((?<=(?<=\s)|(?<=\A))(\w*([_]\w*)+)(?=(?=\W)|(?=\Z)))"  # _ 를 포함한 단어인 경우. (-도 포함했더니.. "pre-trained입니다." 식으로 해석을 방해하는 경우가 생김)
    REG_REPLACER = rf"{REG_CAPITAL_PREFIX}|{REG_ALL_CAPITAL_AT_SENT_START}|{REG_HAVE_UNDERSCORE}"

    def __init__(
        self, source_text: str, api_client_id: str, api_client_secret: str, term_en_list: list = None, verbose=False
    ):
        self.source_text = source_text
        self.api_client_id = api_client_id
        self.api_client_secret = api_client_secret
        self.main_lang = "ko"
        self.sub_lang = "en"

        self.term_en_list = term_en_list

        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        logger.info(gen_log_text(self.source_text))
        # 1. Detect source_lang and set target_lang
        self.source_lang = Translator.identify_lang(source_text, 200)
        if self.source_lang not in Translator.CAN_LANG:
            raise ValueError

        self.target_lang = self.sub_lang if self.source_lang is self.main_lang else self.main_lang
        logger.debug(gen_log_text(self.source_lang, self.target_lang))

    @staticmethod
    def identify_lang(text, check_to_num=-1):
        # max_char_num = 100
        # max_token_num = 20
        # if len(text) > max_char_num:
        #     text = text.split()[:max_token_num]

        # # Use fasttext
        # lang_detect_model = fasttext.load_model('models/fasttext_lid.176.ftz')
        # result = lang_detect_model.predict(text) #  k=2,  # '__label__en'
        # lang = result[0][0].split('__')[-1]

        def isKoreanIncluded(text, check_to_num=check_to_num):
            """
            Check whether the text have korean unicode or not
            https://arisri.tistory.com/267
            """
            check_to_num = min(len(text) - 1, check_to_num)

            for i in text[:check_to_num]:
                if (
                    ord(i) > int("0x1100", 16)
                    and ord(i) < int("0x11ff", 16)
                    or ord(i) > int("0x3131", 16)
                    and ord(i) < int("0x318e", 16)
                    or ord(i) > int("0xa960", 16)
                    and ord(i) < int("0xa97c", 16)
                    or ord(i) > int("0xac00", 16)
                    and ord(i) < int("0xd7a3", 16)
                    or ord(i) > int("0xd7b0", 16)
                    and ord(i) < int("0xd7fb", 16)
                ):
                    return True

            return False

        isKorean = isKoreanIncluded(text, check_to_num)

        return "ko" if isKorean else "en"

    @staticmethod
    def _replace_ne_to_special_token(text, ne_list):
        """
        시도1:처음에는 ner 단어를 활용해서 대치하려고 했으나
        어떤 경우에는 그 기호 안에 있는 ner도 해석해버리는 경우가 많고, 다른 단어 해석에도 영향을 미칠 수 있음에 따라
        시도2: 'NER1'과 같이 보통 문장 쓸 떄도 키워드를 지칭해주는 방식으로 바꿔주고 + 의미없는 NER을 붙여줘서 바꿔주고
        추후다시 대치하는 방식으로 사용
        근데 다시 여러가지 실험하다 보니 해당 단어를 지우고 '[1]'이나 '[NE1]', '[N1E]', 그냥 단어 양옆에 '' 넣어주는 등으로 대체하는게 아래 같은 텍스트 번역을 이상하게 만듦
            Gunicorn forks multiple system processes within each dyno to allow a Python app to support multiple concurrent requests without requiring them to be thread-safe. In Gunicorn terminology, these are referred to as worker processes (not to be confused with Heroku worker processes, which run in their own dynos).
        이건 계속 그대로인 예제: Then you will add the following line in your Procfile
        시도3: 그래서
        영어는 그냥 단어를 모두 대문자로 바꿨다가 원복해주는 방식으로. 한국어는 해당 문자에 '' 붙여줬다가 복원
        참고: 중요한 부분을 두드러지게 할 때 https://thoughts.chkwon.net/punctuation-korean-english/
        한글에서는 ‘드러냄표’ 혹은 ‘밑줄’을 사용하는 것을 기본으로 ‘작은따옴표’의 사용도 허락한다.
        - 영어에서는 italics(이탤릭체)를 주로 사용하며, 때에 따라서 boldface(굵은 글씨체), underline(밑줄) 등을 사용하기도 한다.
        어떤 이는 single quotation mark(작은 따옴표) 혹은 double quotation mark(큰 따옴표)를 사용하기도 하나, 일반적으로 잘못된 용법이라고 한다.
        시도4: 트위터 태그를 활용한 @TAG1 방식으로.
        시도5: @TAG1을 바꿀 때 @TAG11까지 바뀌는 문제 존재. 단순히 순서를 역순으로 해줄까 하다가
        조사 을/를 문제까지 처리해주기 위해 @1끝자리대문자 형태로 바꿔줌
        """
        # ner_set = set()
        # for ner_tuple in ner_results:
        #     if ner_tuple[1] != 'O':  # NER
        #         ner_set.add(ner_tuple[0])
        # joined_ner = '|'.join(ner_set)
        # prep_text = re.sub(f'(\W|^)({joined_ner})(\W|$)', r'\1[/\2/]\3', text)

        detected_ne_set = set()

        # 대치한 경우를 모두 dict에 담아줘서 추후 다시 복구하는게 안전할 것 같지만...  replaced_dict = {}

        # 1. ne detection model 사용
        # ner_model = ner_models[lang]
        # ner_results = ner_model(text)

        # for ner_tuple in ner_results:
        #     if ner_tuple[1] != 'O':
        #         # print(ner_tuple[0])
        #         detected_ne_set.add(ner_tuple[0])
        # print("1. Detected NEs: ", detected_ne_set)

        # 2. Reg replacement
        match_objs = re.finditer(Translator.REG_REPLACER, text)
        reg_detected_ne_set = {match_obj.group() for match_obj in match_objs}

        logger.debug(gen_log_text(reg_detected_ne_set))
        detected_ne_set.update(reg_detected_ne_set)

        # 3. predefiend_ne_set을 대소문자 구분없이 명확히 일치하는 token(또는 그 token을 포함하여 -로 연결되어 있는 token 전체 ) 찾아내기
        predefiend_detected_ne_set = set()
        if ne_list is not None:
            # for predefiend_ne in ne_list:
            #     from_reg = re.compile(f'(?<=(?<=\s)|(?<=\A)){predefiend_ne}(?=(?=\W)|(?=\Z))', re.IGNORECASE)
            #     match_objs = re.finditer(from_reg, text)
            #     predefiend_detected_ne_set.update({match_obj.group() for match_obj in match_objs})

            joined_term = "|".join(ne_list)
            from_reg = re.compile(
                r"(?<=(?<=\s)|(?<=\A))([a-zA-Z0-9]*[-])*("
                + joined_term
                + r")(es|s){,1}([-][a-zA-Z0-9]*)*(?=(?=\W)|(?=\Z))",
                re.IGNORECASE,
            )
            match_objs = re.finditer(from_reg, text)
            predefiend_detected_ne_set.update({match_obj.group() for match_obj in match_objs})

        logger.debug(gen_log_text(predefiend_detected_ne_set))
        detected_ne_set.update(predefiend_detected_ne_set)

        detected_ne_set = detected_ne_set - Translator.TO_BE_REMOVED_TERM_LIST

        # 1+2+3 대치. 사용자가 넣은 문장 안에서 찾은 결과이기 때문에 찾은것 그대로만(대소문자 구분 등) 찾아서 대치
        # 물론 해당 자리의 단어가 아닌 다른 자리 단어또한 대치될 위험성도 존재하나...
        prep_text = text
        detected_ne_list = list(detected_ne_set)
        for idx, ne in enumerate(detected_ne_list):
            # print(term)
            # 앞에 무조건 공백이나 문장시작. 뒤에는 단어만 아니면 공백이나 기호도 올수 있음(그 기호는 그대로 놔둠)
            # 예시문장:  data  .data.  SS-data df data  sf-data-sdf data.
            # data data data. 는 대치. .data. SS-data sf-data-sdf 등은 대치하지 않음
            from_reg = re.compile(rf"(?<=(?<=\s)|(?<=\A)){ne}(?=(?=\W)|(?=\Z))")
            # to_str = f"{ne.upper()}" if source_lang == 'en' \
            #         else f"'{ne}'" # ko 경우.       f"'[{idx}]'"
            to_str = f"@{idx}{get_last_char(ne).upper()}"

            prep_text = re.sub(from_reg, to_str, prep_text)
        logger.debug(gen_log_text(detected_ne_list))

        return prep_text, detected_ne_list

    @staticmethod
    def _post_correction(translated_text):
        text = translated_text.replace("@ ", " @")
        # text = re.sub(r"(\S)(@)", "\1 \2", text)
        return text

    @staticmethod
    def _restore_ne(translated_text, ne_list: list):
        # re.sub(r"'(NER)(\d+)'", rf"{ne_list[\2]}", translated_text)  # 변수 안에 reg ㅍ현이 들어가야 하는데 어떻게 하느거지..
        # if self.source_lang == 'en':
        #     for idx, ne in enumerate(ne_list):
        #         translated_text = translated_text.replace(ne.upper(), ne)
        # elif self.source_lang == 'ko':
        #     for idx, ne in enumerate(ne_list):
        #         translated_text = re.sub(rf"'{ne}'", ne, translated_text)   #rf"'\[{idx}\]'"
        # else:
        #     print("error")

        for idx, ne in reversed(list(enumerate(ne_list))):  # 순서대로 하면 @11N 이 @1 대체할 때 대체되어버림. 그래서 역순으로
            translated_text = translated_text.replace(f"@{idx}{get_last_char(ne).upper()}", ne)

        return translated_text

    def _request_translate(self, prep_source_text):
        data = {"text": prep_source_text, "source": self.source_lang, "target": self.target_lang}

        header = {
            # 'content-type': 'application/json; charset=UTF-8',
            "X-Naver-Client-Id": self.api_client_id,
            "X-Naver-Client-Secret": self.api_client_secret,
        }
        logger.info(gen_log_text(data, self.api_client_id))

        response = requests.post(Translator.BASE_URL, headers=header, data=data)
        rescode = response.status_code

        if rescode == 200:
            t_data = response.json()
            translated_text = t_data["message"]["result"]["translatedText"]

            return translated_text, rescode

        else:
            logger.error(gen_log_text(rescode))
            return None, rescode

    def translate(self):
        """
        main_lang: 사용자는 원문 클릭 시, 번역되어 보이는 언어(target language).
            단 source_text가 main_lang인 경우는 아래 sub_lang이 target language으로 역할)
        sub_lang: source_text가 main_lang인 경우 target language
        """

        # 2. Detect NE and replace it
        if self.source_lang == "en":
            prep_source_text, ners = Translator._replace_ne_to_special_token(self.source_text, self.term_en_list)
        else:
            prep_source_text = self.source_text
        logger.debug(gen_log_text(prep_source_text))

        # 3. Translation
        translated_text, rescode = self._request_translate(prep_source_text)
        logger.debug(gen_log_text(translated_text))

        if translated_text is None:
            logger.error(gen_log_text(rescode))
            return None, rescode

        else:
            corrected_text = Translator._post_correction(translated_text)
            logger.debug(gen_log_text(corrected_text))

            result_text = Translator._restore_ne(corrected_text, ners) if self.source_lang == "en" else translated_text
            logger.info(gen_log_text(result_text))

            return result_text, rescode
