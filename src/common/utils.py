import json
import os
import pickle
import re
from pathlib import Path
from typing import Collection, Union

import orjson
from chardet.universaldetector import UniversalDetector

from src.common.base import EmptyFileError


def get_suffix(path: Union[str, Path]):
    """Path에서 suffix 부분을 리턴히는 함수
    그냥 .with_suffix("")를 쓰면 SDRW2000000001.1 와 같은 형태가 들어왔을 때, '.1'가 삭제됨에 따라
    이를 유지시켜주기 위한 처리를 포함하고 있음
    """
    path = Path(path)

    suffix = path.suffix[1:]
    if len(suffix) >= 2 and re.search("[a-zA-Z]", path.suffix):
        return path.suffix
    else:
        return ""


def load_obj(file_path: Union[str, Path], file_type: str = None, encoding: str = "utf-8", verbose: bool = False):
    """file_type과 encoding이 주어지지 않아도 해당 file_path에 맞는 적절한 값을 찾아 파일을 불러와주는 함수
    - 주어진 encoding 값으로 load 시 encoding 관련 오류가 발생했다면, 적절한 encoding을 찾아 재시도함
    """

    def _load_obj(file_path, encoding):
        # encoding = detect_encoding(file_path) if use_encoding_detector else "utf-8"

        if file_type in [".pickle", ".pkl", ".p"]:
            mode = "rb"
            with open(file_path, mode) as f:
                result = pickle.load(f)

        else:
            mode = "r"
            with open(file_path, mode, encoding=encoding) as f:
                if file_type == ".json":
                    result = json.load(f)

                elif file_type == ".jsonl":
                    json_list = list(f)
                    jsons = []
                    for json_str in json_list:
                        line = json.loads(json_str)  # 문자열을 읽을때는 loads
                        jsons.append(line)
                    result = jsons

                else:
                    lines = f.read().splitlines()
                    result = lines

        return result

    if os.path.getsize(file_path) == 0:
        raise EmptyFileError(f"The file {file_path} is empty")

    if file_type is None:
        file_type = get_suffix(file_path)

    try:
        result = _load_obj(file_path, encoding)
    except UnicodeDecodeError as e:  # may encoding problem
        try:
            encoding_fix = detect_encoding(file_path)
            result = _load_obj(file_path, encoding_fix)
        except Exception as e:
            print(f"Fail to load '{file_path}")
            raise e
        else:
            print(
                f"The appropriate file encoding value is {encoding_fix} not {encoding}. If you designate 'encoding={encoding_fix}', you'll be able to read the file faster"
            )
            encoding = encoding_fix

    if verbose:
        print(f"Success to load '{file_path}', with encoding='{encoding}'")
    return result


def detect_encoding(file_path: Union[str, Path]):
    encoding_detector = UniversalDetector()

    # print(file_path)
    encoding_detector.reset()
    for line in open(file_path, "rb"):
        encoding_detector.feed(line)
        if encoding_detector.done:
            break
    encoding_detector.close()

    result = encoding_detector.result  # {'encoding': 'EUC-KR', 'confidence': 0.99, 'language': 'Korean'}
    encoding = result["encoding"]

    # Use cp949(extension version of EUC-KR) instead of EUC-KR
    if encoding == "EUC-KR":
        encoding = "cp949"

    return encoding


def save_obj(collection: Collection, path: Union[str, Path], verbose: bool = True):
    def default_serializer(obj):
        if isinstance(obj, set):
            return list(obj)

    _, file_extension = os.path.splitext(os.path.basename(path))

    # Make dirs
    dir_path = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_path, exist_ok=True)

    if file_extension in [".pickle", ".pkl", ".p"]:
        with open(path, "wb") as f:
            pickle.dump(collection, f)

    else:
        with open(path, "wb") as f:
            f.write(
                orjson.dumps(
                    collection,
                    option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2 | orjson.OPT_SERIALIZE_NUMPY,
                    default=default_serializer,
                )
            )
    if verbose:
        print(f"Save to {path}")
