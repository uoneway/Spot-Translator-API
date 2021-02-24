import requests
from bs4 import BeautifulSoup
import pickle
import re
import logging
from varname import argname


def get_ml_terms():
    """
    Get terms related with ML from google machine-learning page
    """

    url = 'https://developers.google.com/machine-learning/glossary'
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text)
    # print(soup.prettify())

    terms_html = soup.select('h2.hide-from-toc')

    term_set = set()
    for term_html in terms_html:
        terms = re.split('\(|\)', term_html.text)  # ROC (receiver operating characteristic) Curve 같은 케이스 존재. 원래라면 양옆거 이어줘야 하지만... 일단은 그냥 별개로
        # if(len(terms) > 1):
        #     print(terms)
        for term in terms:
            term = term.strip()
            if term == '':
                continue
            term_set.add(term)  # term_set.update(term_html.text.split())

    # print(len(term_set))
    return term_set


def save_obj(obj, filename, path='.'):  
    with open(f'{path}/{filename}', 'wb') as f:
        pickle.dump(obj, f)

def load_obj(filename, path='.'):
    with open(f'{path}/{filename}', 'rb') as f:
        return pickle.load(f)


def __get_logger():
    """로거 인스턴스 반환
    """

    logger = logging.getLogger('logger')

    # Check handler exists
    if len(logger.handlers) > 0:
        return logger # Logger already exists. 동일 로거가 존재하는데 다시 핸들러를 add하면  중복해서 메시지 출력됨 https://5kyc1ad.tistory.com/269

    # 스트림 핸들러 정의
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)

    # 로그 포멧 정의
    formatter = logging.Formatter(
        '(%(asctime)s  %(relativeCreated)d)  [%(levelname)s]  %(filename)s, %(lineno)s line \n>> %(message)s', datefmt='%Y%m%d %H:%M:%S') 
    stream_handler.setFormatter(formatter)
    
    # 로그 레벨 정의
    logger.setLevel(logging.DEBUG)

    return logger


def gen_log_text(*vars, title=None):  # pre_text=None,
    var_names = argname(vars)

    name_space = 25
    value_space = 50

    text = f'<{title}>\n' if title is not None else ''
    for idx, var_tuple in enumerate(zip(var_names, vars)):
        if isinstance(var_tuple[1], str):
            text += f'{var_tuple[0]:<{name_space}}: {var_tuple[1]:<{value_space}}' if idx == 0 else \
                   f' \n>> {var_tuple[0]:<{name_space}}: {var_tuple[1]:<{value_space}}'
        else:
            text += f'{var_tuple[0]:<{name_space}}: {var_tuple[1]}' if idx == 0 else \
                    f' \n>> {var_tuple[0]:<{name_space}}: {var_tuple[1]}'

    # return f"{text}" if pre_text is None else \
    #         f"{pre_text} {text}"
    return f"{text}"


if __name__ == '__main__':
    term_set = get_ml_terms()
    save_obj(term_set, "ml_term_set.pkl", './datasets')
    # terms = load_obj("ml_term_set", "./datasets")
    # print(terms)
