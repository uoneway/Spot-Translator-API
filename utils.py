import requests
from bs4 import BeautifulSoup
import pickle


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
        terms = term_html.text.split('(')

        for term in terms:
            term = term.strip().strip(')')
            term_set.add(term)  # term_set.update(term_html.text.split())

    # print(len(term_set))
    return term_set


def save_obj(obj, filename, path='.'):  
    with open(f'{path}/{filename}.pkl', 'wb') as f:
        pickle.dump(obj, f)

def load_obj(filename, path='.'):
    with open(f'{path}/{filename}.pkl', 'rb') as f:
        return pickle.load(f)


if __name__ == '__main__':
    term_set = get_ml_terms()
    save_obj(term_set, "ml_term_set", './datasets')
    # terms = load_obj("ml_term_set", "./datasets")
    # print(terms)
