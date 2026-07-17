from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from app.db import db_connection
import jwt


#Código de retorno da API
StatusCodesAPI = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500
}

#Carregar variáveis de ambiente
load_dotenv()


SECRET_KEY = os.environ.get('SECRET_KEY')

###
### FUNÇÃO PARA RETORNAR TOKEN FORNECIDO NO HEADER 'AUTHORIZATION'
###
def get_token_info(token):

    
    payload = jwt.decode(token, SECRET_KEY, algorithms="HS256")
    
    nome = payload["nome"]
    id_pessoa = payload["id_pessoa"]
    tipo = payload["tipo"]
    
    return nome, id_pessoa, tipo



#BLUEPRINTS DAS ROTAS
from app.routes.reservas import reservas_bp
from app.routes.salas import salas_bp
from app.routes.auth import auth_bp


app = Flask(__name__, template_folder='../Frontend')

#Registar as blueprints na app "principal"
app.register_blueprint(auth_bp)
app.register_blueprint(salas_bp)
app.register_blueprint(reservas_bp)

@app.route('/')
def index():
    
    frontend_dir = os.path.abspath(os.path.join(app.root_path, '../Frontend'))
    return send_from_directory(frontend_dir, 'index.html')


CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500", "https://reserva-de-salas.onrender.com", "https://html-reserva-de-saas.onrender.com"])