from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.common.base import logger
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
async def translate(request: Request):
    logger.info("------------------------------------Get a new request------------------------------------")

    req_info = await request.json()
    api_client_info = req_info.get("api_client_info")
    data = req_info.get("data")
    main_tgt_lang = data.get("main_tgt_lang", "ko")
    sub_tgt_lang = data.get("sub_tgt_lang", "en")

    # term_en_set =  Translator.BASE_TERM_EN_SET if self.user_defined_term_set is None \
    #     else (Translator.BASE_TERM_EN_SET | self.user_defined_term_set)
    # term_en_list = BASE_TERM_EN_LIST

    translator = PapagoTranslator(
        api_client_id=api_client_info["id"],
        api_client_secret=api_client_info["secret"],
        main_tgt_lang=main_tgt_lang,
        sub_tgt_lang=sub_tgt_lang
        # term_en_list=term_en_list,
    )

    translated_text, status_msg = translator.run(src_text=data["source_text"], tgt_lang="ko")  # data["tgt_lang"]
    if translated_text is None:
        translator = GoogleTranslator()
        translated_text, status_msg = translator.run(src_text=data["source_text"], tgt_lang="ko")

    response_dict = {"message": {"result": {"translatedText": translated_text, "api_rescode": status_msg}}}
    response_json = jsonable_encoder(response_dict)

    return JSONResponse(content=response_json)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)  # uvicorn main:app --reload
