from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.common.base import logger
from src.common.models import TranslateRequest, TranslatorType, UserOption
from src.common.utils import load_obj
from src.translate.translator import GoogleTranslator, PapagoTranslator

app = FastAPI(title="On the spot Translator API", version="1.0")

TERM_EN_DIR = Path("src/translate/term_set")
BASE_TERM_EN_FILES = ["ml_terms_google_picked.txt", "ml_terms_manual.txt"]
BASE_TERM_EN_SET = set()
for filename in BASE_TERM_EN_FILES:
    BASE_TERM_EN_LIST = load_obj(TERM_EN_DIR / filename)
    BASE_TERM_EN_SET.update(BASE_TERM_EN_LIST)
BASE_TERM_EN_LIST = list(BASE_TERM_EN_SET)


@app.post("/translate")
def translate(translate_request: TranslateRequest, user_option: Optional[UserOption] = None):
    logger.info(f"{'-'*10} New request: {asdict(translate_request)} {'-'*10}")
    logger.debug(f"User option: {asdict(user_option)}")

    match user_option.translator_client_info.translator_type:
        case TranslatorType.papago:
            translator = PapagoTranslator(user_option)
        case TranslatorType.google | _:
            translator = GoogleTranslator()

    # term_en_set =  Translator.BASE_TERM_EN_SET if self.user_defined_term_set is None \
    #     else (Translator.BASE_TERM_EN_SET | self.user_defined_term_set)
    # term_en_list = BASE_TERM_EN_LIST

    tgt_lang = "ko"  # translate_request.tgt_lang
    translated_text, status_msg = translator.run(src_text=translate_request.src_text, tgt_lang=tgt_lang)
    if translated_text is None and not isinstance(translator, GoogleTranslator):
        logger.info(f"{user_option.translator_client_info.translator_type} API failed. Try Google API")
        translator = GoogleTranslator()
        translated_text, status_msg = translator.run(src_text=translate_request.src_text, tgt_lang=tgt_lang)

        if translated_text is None:
            logger.info("Google API also failed")
            translated_text = None
            status_msg = "API failed"
            return JSONResponse(
                content={"message": {"result": {"translatedText": translated_text, "api_rescode": status_msg}}},
                status_code=400,
            )

    response_dict = {"message": {"result": {"translatedText": translated_text, "api_rescode": status_msg}}}
    response_json = jsonable_encoder(response_dict)
    return JSONResponse(content=response_json, status_code=200)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)  # uvicorn main:app --reload
