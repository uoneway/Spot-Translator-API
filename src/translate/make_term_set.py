import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from src.common.utils import save_obj


def crawl_google_ml_terms():
    """
    Get terms related with ML from google machine-learning page
    """

    url = "https://developers.google.com/machine-learning/glossary"
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text)
    # print(soup.prettify())

    terms_html = soup.select("h2.hide-from-toc")

    term_set = set()
    for term_html in terms_html:
        terms = re.split(
            r"\(|\)", term_html.text
        )  # ROC (receiver operating characteristic) Curve 같은 케이스 존재. 원래라면 양옆거 이어줘야 하지만... 일단은 그냥 별개로
        # if(len(terms) > 1):
        #     print(terms)
        for term in terms:
            term = term.strip()
            if term == "":
                continue
            term_set.add(term)  # term_set.update(term_html.text.split())

    # print(len(term_set))
    term_list = sorted(list(term_set))

    return term_list


if __name__ == "__main__":
    now = datetime.today().strftime("%Y%m%d-%H%M")
    term_set = crawl_google_ml_terms()
    save_obj(term_set, f"term_set/raw/ml_terms_google_{now}.txt")
    # terms = load_obj("ml_term_set", "./datasets")
    # print(terms)
