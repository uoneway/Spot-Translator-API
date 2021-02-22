import requests
from bs4 import BeautifulSoup
import pickle
import re


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


if __name__ == '__main__':
    term_set = get_ml_terms()
    save_obj(term_set, "ml_term_set.pkl", './datasets')
    # terms = load_obj("ml_term_set", "./datasets")
    # print(terms)
