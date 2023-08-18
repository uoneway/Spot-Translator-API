import re
from abc import ABCMeta, abstractmethod
from functools import lru_cache
from typing import Optional, Tuple

import httpx
from googletrans import Translator as GoogleTrans

from src.common.base import gen_log_text, logger
from src.common.models import UserOption
from src.translate.utils import isKoreanIncluded


class Translator(metaclass=ABCMeta):
    MAX_CHAR_PER_REQ = None

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
        (기호가 쓰여져서) 문장이 끝나는 것으로 보이는 지점을 찾아 그 기준으로 나눈다.
        """

        def _get_split_idx(s: str) -> int:
            match = re.finditer(r"[.:;!?<>()\[\]]", s[::-1])

            index = None
            for m in match:
                print(len(s), m.start())
                index = len(s) - m.start()
                break
            return index

        if len(text) > cls.MAX_CHAR_PER_REQ:
            split_idx = _get_split_idx(text[: cls.MAX_CHAR_PER_REQ])
            text = text[:split_idx]
        return text.strip()

    @classmethod
    def postprocess(cls, text: str) -> str:
        return text

    @abstractmethod
    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[str]]:
        return None, None

    @lru_cache(maxsize=10)
    async def run(self, src_text: str, tgt_lang: str = None) -> Tuple[Optional[str], int]:
        logger.info(gen_log_text(src_text))

        src_text = self.preprocess(src_text)

        # 1. Detect src_lang and set tgt_lang
        src_lang = Translator.identify_lang(src_text)
        if tgt_lang is None:
            tgt_lang = self.main_tgt_lang if src_lang != self.main_tgt_lang else self.sub_tgt_lang
        logger.debug(gen_log_text(src_lang, tgt_lang))

        # 2. Translation
        translated_text, resp_code = await self.translate(src_text=src_text, src_lang=src_lang, tgt_lang=tgt_lang)
        logger.debug(gen_log_text(translated_text))

        if translated_text is None:
            logger.error(gen_log_text(resp_code))
            return None, resp_code

        else:
            result_text = self.postprocess(translated_text)
            logger.info(gen_log_text(result_text))

            return result_text, resp_code


class PapagoTranslator(Translator):
    # https://developers.naver.com/docs/papago/papago-nmt-overview.md
    REQ_URL = "https://openapi.naver.com/v1/papago/n2mt"
    MAX_CHAR_PER_REQ = 5000
    MAX_CHAR_PER_DAY = 10000

    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[str]]:
        data = {"text": src_text, "source": src_lang, "target": tgt_lang}
        header = {
            # 'content-type': 'application/json; charset=UTF-8',
            "X-Naver-Client-Id": self.api_key,
            "X-Naver-Client-Secret": self.secret_key,
        }
        logger.debug(gen_log_text(data, self.api_key))

        async with httpx.AsyncClient() as client:
            response = await client.post(PapagoTranslator.REQ_URL, headers=header, data=data)
            status_code = response.status_code

        if status_code == 200:
            t_data = response.json()
            translated_text = t_data["message"]["result"]["translatedText"]

            return translated_text, None

        else:
            status_msg = PapagoTranslator.convert_status_code_to_msg(status_code)
            logger.error(gen_log_text(status_msg))
            return None, status_msg

    def convert_status_code_to_msg(status_code):
        # https://developers.naver.com/docs/common/openapiguide/
        # errorcode.md#%EC%98%A4%EB%A5%98-%EB%A9%94%EC%8B%9C%EC%A7%80-%ED%98%95%EC%8B%9D

        msg_forForDetail = (
            "</br>For more details, click"
            + "<a target='_blank' "
            + "href='https://uoneway.notion.site/On-the-spot-Translator-1826d87aa2d845d093793cee0ca11b29'"
            + " style='color: #008eff; pointer-events: all;'><u>here</u></a>"
        )
        if status_code == 401:
            msg = (
                "🔧 Authentication failed: </br>"
                + "Please make sure you enter correct 'Naver API application info(Client ID and Client Secret)'"
                + " in the option popup."
                + msg_forForDetail
            )
        elif status_code == 403:
            msg = (
                "🔧 You don't have the 'Papago Translation API' permission: </br>"
                + "Please add 'Papago Translation' on 'API setting' tab in the Naver Developer Center website."
                + msg_forForDetail
            )
        elif status_code == 429:
            msg = (
                "⏳ Used up all your daily usage: </br>"
                + "This translator use Naver Papago API which provide only 10,000 characters translation per a day."
            )
        else:
            msg = "❗ Error: </br>Some problem occured at Naver Papago API. Please try again in a few minutes"

        return msg


class GoogleTranslator(Translator):
    # https://github.com/ssut/py-googletrans
    # https://py-googletrans.readthedocs.io/en/latest/
    # https://pypi.org/project/googletrans/
    MAX_CHAR_PER_REQ = 15000

    def __init__(self):
        self.translator = GoogleTrans()

    async def translate(self, src_text: str, src_lang: str, tgt_lang: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            resp = self.translator.translate(src_text, src=src_lang, dest=tgt_lang)
            # resp.pronunciation: "oneul-eun wol-yoil-ibnida",
            return resp.text, None

        except Exception:
            status_msg = "❗ Error: </br>Some problem occured at googletrans. Please try again in a few minutes"
            return None, status_msg
