from flask import Flask, request  # 서버 구현을 위한 Flask 객체 import
from flask_restx import Api, Resource  # Api 구현을 위한 Api 객체 import
from translator import Translator
from utils import __get_logger, load_obj

logger = __get_logger()

app = Flask(__name__)  # Flask 객체 선언, 파라미터로 어플리케이션 패키지의 이름을 넣어줌.
api = Api(app, version='1.0', title='On the spot Translator API',  # Flask 객체에 Api 객체 등록
        description='Click and see the translation right below which keeps named entity in the original text.',
)

BASE_TERM_EN_PATH = 'datasets/terms_en.txt'  # 'datasets/ml_term_set.pkl'
BASE_TERM_EN_LIST = load_obj(BASE_TERM_EN_PATH)
BASE_TERM_EN_SET = set(BASE_TERM_EN_LIST)


@api.route('/translate')
class Translate(Resource):
    def post(self):
        logger.info("------------------------------------Get a new request------------------------------------")

        api_client_info = request.json.get('api_client_info')
        data = request.json.get('data')

        # term_en_set =  Translator.BASE_TERM_EN_SET if self.user_defined_term_set is None \
        #     else (Translator.BASE_TERM_EN_SET | self.user_defined_term_set)
        term_en_list = BASE_TERM_EN_LIST
        translator = Translator(data['source_text'],
                                api_client_info['id'], api_client_info['secret'],
                                term_en_list)
        translated_text, api_rescode = translator.translate()

        return {
            'message': {
                'result': {
                    'translatedText': translated_text,
                    'api_rescode': api_rescode
                }
            }
        }


# @api.route('/todos/<int:todo_id>')
# class TodoSimple(Resource):
#     def get(self, todo_id):  # GET 요청시 리턴 값에 해당 하는 dict를 JSON 형태로 반환
#         return {
#             'todo_id': todo_id,
#             'data': todos[todo_id]
#         }

#     def put(self, todo_id):
#         todos[todo_id] = request.json.get('data')
#         return {
#             'todo_id': todo_id,
#             'data': todos[todo_id]
#         }
    
#     def delete(self, todo_id):
#         del todos[todo_id]
#         return {
#             "delete" : "success"
#         }

if __name__ == "__main__":
    app.run(debug=True)
