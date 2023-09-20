import re
from abc import abstractmethod
from functools import lru_cache
from typing import Optional, Tuple

import httpx
from googletrans import Translator as GoogleTrans

from src.common.base import gen_log_text, logger
from src.common.models import APIErrorCode, UserOption
from src.translate.utils import isKoreanIncluded


class Translator:
    SERVICE_NAME: str
    error_code: APIErrorCode
    MAX_CHAR_PER_REQ: int = None

    def __init__(
        self,
        user_option: Optional[UserOption],
        term_en_list: list = None,
    ):
        """
        main_lang: 사용자는 원문 클릭 시, 번역되어 보이는 언어(target language).
            단 source_text가 main_lang인 경우는 아래 sub_lang이 target language으로 역할)
        sub_lang: source_text가 main_lang인 경우 target language
        """
        self.api_key = user_option.translator_client_info.api_key
        self.secret_key = user_option.translator_client_info.secret_key

        self.main_tgt_lang = user_option.main_tgt_lang
        self.sub_tgt_lang = user_option.sub_tgt_lang
        # self.term_en_list = term_en_list

    @staticmethod
    @lru_cache(maxsize=10)
    def identify_lang(text: str, char_num_to_check: int = 30) -> str:
        chars_prefix = text[:char_num_to_check]  # text.split()[:max_token_num]

        isKorean = isKoreanIncluded(chars_prefix)
        if isKorean:
            lang = "ko"
        else:
            try:
                google_translator = GoogleTrans()
                lang = google_translator.detect(chars_prefix).lang
            except Exception:
                logger.error("'google_translator.detect' raise error. Just regard it as English")
                lang = "en"

        return lang

    @classmethod
    def preprocess(cls, text: str) -> str:
        """주어진 text가 MAX_CHAR_PER_REQ를 넘는 경우는
        일단 MAX_CHAR_PER_REQ 길이만큼 만든 다음에
        (기호가 쓰여져서) 문장이 끝나는 것으로 보이는 지점을 찾아 그 기준으로 나누고 뒷 부분은 버림
        TODO: 문장 단위로 나눠서 여러번 호출 또는 batch로 호출하도록 수정
        """
        ELLIPSIS_SYMBOL = "..."

        def _get_split_idx(s: str) -> int:
            match = re.finditer(r"[.:;!?<>()\[\]]", s[::-1])

            index = None
            for m in match:
                print(len(s), m.start())
                index = len(s) - m.start()
                break
            return index

        if cls.MAX_CHAR_PER_REQ is not None and len(text) > cls.MAX_CHAR_PER_REQ:
            split_idx = _get_split_idx(text[: cls.MAX_CHAR_PER_REQ - len(ELLIPSIS_SYMBOL)])
            text = text[:split_idx] + ELLIPSIS_SYMBOL
            logger.warning(f"Since rext is longger than {cls.MAX_CHAR_PER_REQ}, only front part would be translated")
        return text.strip()

    @classmethod
    def postprocess(cls, text: str) -> str:
        return text.strip()

    @abstractmethod
    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[int]]:
        return None, None

    @lru_cache(maxsize=10)
    async def run(self, src_text: str, tgt_lang: str = None) -> Tuple[Optional[str], Optional[str]]:
        """translated_text, error_msg 를 리턴"""
        src_text = self.preprocess(src_text)
        logger.info(f"Text to translate: '{src_text}'")
        if not src_text:
            return "", "❗ Empty text"

        # 1. Detect src_lang and set tgt_lang
        src_lang = Translator.identify_lang(src_text)
        if tgt_lang is None:
            tgt_lang = self.main_tgt_lang if src_lang != self.main_tgt_lang else self.sub_tgt_lang
        logger.info(f"Language: {src_lang} (detected) -> {tgt_lang}")

        # 2. Translate
        translated_text, status_code = await self.translate(src_text=src_text, src_lang=src_lang, tgt_lang=tgt_lang)
        if translated_text is not None:
            translated_text = self.postprocess(translated_text)
            logger.info(f"Translated text: {translated_text}")
            return translated_text, None
        else:
            error_msg = self.__class__.error_code.convert_to_msg(status_code)
            logger.error(f"{error_msg}")
            return None, error_msg


class PapagoTranslator(Translator):
    """
    - https://developers.naver.com/docs/papago/papago-nmt-overview.md
    - https://developers.naver.com/docs/common/openapiguide/
        errorcode.md#%EC%98%A4%EB%A5%98-%EB%A9%94%EC%8B%9C%EC%A7%80-%ED%98%95%EC%8B%9D
    """

    SERVICE_NAME = "Papago"
    REQUEST_URL = "https://openapi.naver.com/v1/papago/n2mt"
    MAX_CHAR_PER_REQ = 5000
    # MAX_CHAR_PER_DAY = 10000

    error_code = APIErrorCode(service_name=SERVICE_NAME, auth_failed=401, rate_limit_exceeded=429, quota_exceeded=429)

    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[int]]:
        header = {
            # 'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            "X-Naver-Client-Id": self.api_key,
            "X-Naver-Client-Secret": self.secret_key,
        }
        data = {"text": src_text, "source": src_lang, "target": tgt_lang}
        logger.debug(gen_log_text(data))

        async with httpx.AsyncClient() as client:
            response = await client.post(PapagoTranslator.REQUEST_URL, headers=header, data=data)
            status_code = response.status_code

        if status_code == 200:
            t_data = response.json()
            translated_text = t_data["message"]["result"]["translatedText"]
            return translated_text, status_code
        else:
            logger.error(gen_log_text(response.__dict__))
            return None, status_code


class GoogleTranslator(Translator):
    """
    - https://github.com/ssut/py-googletrans
    - https://py-googletrans.readthedocs.io/en/latest/
    - https://pypi.org/project/googletrans/
    """

    SERVICE_NAME = "Google"
    MAX_CHAR_PER_REQ = 15000
    error_code = APIErrorCode(service_name=SERVICE_NAME)
    translator = GoogleTrans()

    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[int]]:
        try:
            response = self.__class__.translator.translate(src_text, src=src_lang, dest=tgt_lang)
            # response.pronunciation: "oneul-eun wol-yoil-ibnida",
            return response.text, None

        except Exception as e:
            logger.error(e)
            status_code = 400
            return None, status_code


class DeepLTranslator(Translator):
    """
    - https://www.deepl.com/ko/docs-api/translate-text/translate-text
    - https://www.deepl.com/ko/docs-api/api-access/error-handling
    """

    SERVICE_NAME = "DeepL"
    MAX_CHAR_PER_REQ = None
    REQUEST_URL = "https://api-free.deepl.com/v2/translate"
    error_code = APIErrorCode(
        service_name=SERVICE_NAME, auth_failed=[401, 403], rate_limit_exceeded=429, quota_exceeded=456
    )

    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[int]]:
        header = {
            "Authorization": "DeepL-Auth-Key " + self.api_key,
            "Content-Type": "application/json",
        }
        data = {"text": [src_text], "source_lang": src_lang, "target_lang": tgt_lang}
        logger.debug(gen_log_text(data))

        async with httpx.AsyncClient() as client:
            response = await client.post(DeepLTranslator.REQUEST_URL, headers=header, json=data)
            status_code = response.status_code

        if status_code == 200:
            resp_data = response.json()
            logger.debug(resp_data)
            # {'translations': [{'detected_source_language': 'EN', 'text': '이동'}]}
            translated_text = resp_data["translations"][0]["text"]
            return translated_text, None

        else:
            logger.error(gen_log_text(response.__dict__))
            return None, status_code
