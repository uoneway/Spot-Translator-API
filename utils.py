import requests
from bs4 import BeautifulSoup
import pickle
import re
import logging
import logging.handlers
from varname import argname


def scrap_terms():
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
    term_list = sorted(list(term_set))
    
    return term_list


def save_obj(obj, full_filename, path='.'):
    filename, extension = full_filename.split('.')
    fullpath = f'{path}/{full_filename}'

    if extension == 'txt':
        with open(fullpath, 'w') as f:
            for item in obj:
                f.write("%s\n" % item)

    else:  # extension == 'pkl'
        with open(fullpath, 'wb') as f:
            pickle.dump(obj, f)

def load_obj(full_filename, path='.'):
    filename, extension = full_filename.split('.')
    fullpath = f'{path}/{full_filename}'

    if extension == 'txt':
        with open(fullpath) as f:
            lines = f.read().splitlines()
            return lines

    else:  # extension == 'pkl'
        with open(fullpath, 'rb') as f:
            return pickle.load(f)


def __get_logger():
    """로거 인스턴스 반환
    """

    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)  # 로그 레벨 정의

    # Check handler exists
    if len(logger.handlers) > 0:
        return logger # Logger already exists. 동일 로거가 존재하는데 다시 핸들러를 add하면  중복해서 메시지 출력됨 https://5kyc1ad.tistory.com/269

    # 스트림 핸들러 생성 및 추가
    stream_handler = logging.StreamHandler()
    # fileHandle 생성 및 추가
    file_handler = logging.handlers.TimedRotatingFileHandler(filename='./logs/log', encoding='utf-8',
                                                            when='midnight', interval=1, backupCount=100
                                                            )
    file_handler.suffix = '-%Y%m%d' # 파일명 끝에 붙여줌; ex. log-20190811
    # file_handler = logging.FileHandler('./logs/my.log')
    
    # 로그 포멧 정의
    formatter = logging.Formatter(
            '(%(asctime)s  %(relativeCreated)d)  [%(levelname)s]  %(filename)s, %(lineno)s line \n>> %(message)s', datefmt='%Y%m%d %H:%M:%S') 
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
    term_set = scrap_terms()
    save_obj(term_set, "google_ml_terms.txt", './datasets')
    # terms = load_obj("ml_term_set", "./datasets")
    # print(terms)
