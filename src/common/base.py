import logging

from varname import argname


def __get_logger():
    """로거 인스턴스 반환"""

    logger = logging.getLogger("logger")
    logger.setLevel(logging.DEBUG)  # 로그 레벨 정의

    # Check handler exists
    if len(logger.handlers) > 0:
        return logger  # Logger already exists. 동일 로거가 존재하는데 다시 핸들러를 add하면  중복해서 메시지 출력됨 https://5kyc1ad.tistory.com/269

    # 스트림 핸들러 생성 및 추가
    stream_handler = logging.StreamHandler()
    # fileHandle 생성 및 추가
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename="./logs/log", encoding="utf-8", when="midnight", interval=1, backupCount=100
    )
    file_handler.suffix = "-%Y%m%d"  # 파일명 끝에 붙여줌; ex. log-20190811
    # file_handler = logging.FileHandler('./logs/my.log')

    # 로그 포멧 정의
    formatter = logging.Formatter(
        "(%(asctime)s  %(relativeCreated)d)  [%(levelname)s]  %(filename)s, %(lineno)s line \n>> %(message)s",
        datefmt="%Y%m%d %H:%M:%S",
    )
    # formatter.converter = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).timetuple()

    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


def gen_log_text(*vars, title=None):  # pre_text=None,
    var_names = argname(vars)

    name_space = 25
    value_space = 50

    text = f"<{title}>\n" if title is not None else ""
    for idx, var_tuple in enumerate(zip(var_names, vars)):
        if isinstance(var_tuple[1], str):
            text += (
                f"{var_tuple[0]:<{name_space}}: {var_tuple[1]:<{value_space}}"
                if idx == 0
                else f" \n>> {var_tuple[0]:<{name_space}}: {var_tuple[1]:<{value_space}}"
            )
        else:
            text += (
                f"{var_tuple[0]:<{name_space}}: {var_tuple[1]}"
                if idx == 0
                else f" \n>> {var_tuple[0]:<{name_space}}: {var_tuple[1]}"
            )

    # return f"{text}" if pre_text is None else \
    #         f"{pre_text} {text}"
    return f"{text}"


class EmptyFileError(Exception):
    def __init__(self, msg: str = None):
        error_msg = "The file is empty" if msg is None else msg
        super().__init__(error_msg)
