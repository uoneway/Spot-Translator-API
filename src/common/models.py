import re
from dataclasses import dataclass, field, fields
from enum import Enum, auto
from typing import Optional


class StrEnum(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class TranslatorType(StrEnum):
    papago: str = auto()
    google: str = auto()
    deepl: str = auto()


@dataclass
class TranslatorClientInfo:
    translator_type: TranslatorType
    api_key: Optional[str] = None
    secret_key: Optional[str] = None


@dataclass
class TranslateRequest:
    src_text: str
    tgt_lang: Optional[str] = None


@dataclass
class UserOption:
    main_tgt_lang: str
    sub_tgt_lang: str
    translator_client_info: Optional[TranslatorClientInfo] = None

    # def to_dict_for_trasnlator(self):
    #     # main_tgt_lang, sub_tgt_lang, api_key, secret_key
    #     result_dict = asdict(self)
    #     del result_dict["translator_client_info"]
    #     if self.translator_client_info is not None:
    #         d = self.translator_client_info.__dict__
    #         del d["translator_type"]
    #         result_dict.update(d)
    #     return result_dict


@dataclass
class APIErrorCode:
    service_name: str
    auth_failed: list[int] = field(default_factory=list)
    rate_limit_exceeded: list[int] = field(default_factory=list)
    quota_exceeded: list[int] = field(default_factory=list)
    internal_error_reg: str = r"4\d\d"
    external_error_reg: str = r"5\d\d"

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, int) and f.type == list[int]:
                setattr(self, f.name, [value])

        self.internal_error_rep = re.compile(self.internal_error_reg)
        self.external_error_rep = re.compile(self.external_error_reg)

    def convert_to_msg(self, status_code: int) -> Optional[str]:
        msgs = []
        if status_code in self.auth_failed:
            msgs.append(
                f"🔒 [{self.service_name}] Authentication Failed:</br>"
                + "- Check the translator API keys you enter in the option popup.</br>"
                + "- Check if you have access permissions to the translator API."
            )
        if status_code in self.rate_limit_exceeded:
            msgs.append(
                f"⏳ [{self.service_name}] Rate Limit Exceeded:</br>"
                + "Too many requests in a short time. Please try again in a few minutes."
            )
        if status_code in self.quota_exceeded:
            msgs.append(f"🚫 [{self.service_name}] Quota Exceeded: </br>Used up all the translator API quota of yours")

        if len(msgs) == 0:
            if self.internal_error_rep.fullmatch(str(status_code)):
                msg = "❗ Some problem occured. Please try again in a few minutes"
            if self.external_error_rep.fullmatch(str(status_code)):
                msg = (
                    f"❗ [{self.service_name}] Some problem occured at the translator API. "
                    + "Please try again in a few minutes"
                )
        elif len(msgs) == 1:
            msg = msgs[0]
        elif len(msgs) > 1:
            msg = "</br>Or</br>".join(msgs)

        appended_msg = (
            "</br>For more details, See"
            + "<a target='_blank' "
            + "href='https://uoneway.notion.site/On-the-spot-Translator-1826d87aa2d845d093793cee0ca11b29'"
            + " style='color: #008eff; pointer-events: all;'><u>On-the-spot-Translator guide page</u></a>"
        )

        return msg + appended_msg
