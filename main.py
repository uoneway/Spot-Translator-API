from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.common.base import __get_logger
from src.common.utils import load_obj
from src.translate.translator import Translator

logger = __get_logger()

app = FastAPI(title="On the spot Translator API", version="1.0")
# uvicorn main:app --reload

TERM_EN_DIR = Path("src/translate/term_set")
BASE_TERM_EN_FILES = ["ml_terms_google_picked.txt", "ml_terms_manual.txt"]
BASE_TERM_EN_SET = set()
for filename in BASE_TERM_EN_FILES:
    BASE_TERM_EN_LIST = load_obj(TERM_EN_DIR / filename)
    BASE_TERM_EN_SET.update(BASE_TERM_EN_LIST)
BASE_TERM_EN_LIST = list(BASE_TERM_EN_SET)


@app.post("/translate")
async def translate(request: Request):
    logger.info("------------------------------------Get a new request------------------------------------")

    req_info = await request.json()
    api_client_info = req_info.get("api_client_info")
    data = req_info.get("data")

    # term_en_set =  Translator.BASE_TERM_EN_SET if self.user_defined_term_set is None \
    #     else (Translator.BASE_TERM_EN_SET | self.user_defined_term_set)
    term_en_list = BASE_TERM_EN_LIST

    translator = Translator(
        source_text=data["source_text"],
        api_client_id=api_client_info["id"],
        api_client_secret=api_client_info["secret"],
        term_en_list=term_en_list,
    )

    translated_text, api_rescode = translator.translate()

    response_dict = {"message": {"result": {"translatedText": translated_text, "api_rescode": api_rescode}}}
    response_json = jsonable_encoder(response_dict)

    return JSONResponse(content=response_json)
