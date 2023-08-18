from dataclasses import dataclass
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


@dataclass
class TranslatorClientInfo:
    translator_type: TranslatorType
    api_key: str
    secret_key: str


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
