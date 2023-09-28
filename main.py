from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.common.base import logger
from src.common.models import TranslateRequest, TranslatorType, UserOption
from src.common.utils import load_obj
from src.translate.translator import DeepLTranslator, GoogleTranslator, PapagoTranslator

app = FastAPI(title="Spot Translator API", version="1.0")

TERM_EN_DIR = Path("data/term_set")
BASE_TERM_EN_FILES = ["ml_terms_google_picked.txt", "ml_terms_manual.txt"]
BASE_TERM_EN_SET = set()
for filename in BASE_TERM_EN_FILES:
    BASE_TERM_EN_LIST = load_obj(TERM_EN_DIR / filename)
    BASE_TERM_EN_SET.update(BASE_TERM_EN_LIST)
BASE_TERM_EN_LIST = list(BASE_TERM_EN_SET)


@app.post("/translate")
async def translate(translate_request: TranslateRequest, user_option: Optional[UserOption] = None):
    translator_type = user_option.translator_client_info.translator_type
    logger.info(f"{'-'*10} New request for {translator_type} {'-'*10}")

    match translator_type:
        case TranslatorType.papago:
            translator = PapagoTranslator(user_option)
        case TranslatorType.deepl:
            translator = DeepLTranslator(user_option)
        case TranslatorType.google:
            translator = GoogleTranslator(user_option)

    # term_en_set =  Translator.BASE_TERM_EN_SET if self.user_defined_term_set is None \
    #     else (Translator.BASE_TERM_EN_SET | self.user_defined_term_set)
    # term_en_list = BASE_TERM_EN_LIST

    status_code = 200
    translated_text, status_msg = await translator.run(
        src_text=translate_request.src_text, tgt_lang=translate_request.tgt_lang
    )
    if translated_text is None and not isinstance(translator, GoogleTranslator):
        logger.error(f"{translator_type} API failed. Try Google API")
        translator_type = TranslatorType.google
        translator = GoogleTranslator(user_option)
        translated_text, _ = await translator.run(
            src_text=translate_request.src_text, tgt_lang=translate_request.tgt_lang
        )

        if translated_text is None:
            logger.error("Google API also failed")
            status_msg = status_msg + "<br/>Google API also failed"
            status_code = 503
        else:
            status_msg = status_msg + "<br/>But translate it by Google API"

    response_dict = {"text": translated_text, "status_msg": status_msg, "translator_type": translator_type}
    response_json = jsonable_encoder(response_dict)
    return JSONResponse(content=response_json, status_code=status_code)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)  # uvicorn main:app --reload
