from flask import Flask
from flask_cors import CORS

from app.db import db_connection

#Código de retorno da API
StatusCodesAPI = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500
}


#BLUEPRINTS DAS ROTAS
from app.routes.reservas import reservas_bp
from app.routes.salas import salas_bp
from app.routes.auth import auth_bp


app = Flask(__name__)

#Registar as blueprints na app "principal"
app.register_blueprint(auth_bp)
app.register_blueprint(salas_bp)
app.register_blueprint(reservas_bp)

CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500", "http://localhost:5500"])