import psycopg
import os
from dotenv import load_dotenv
from psycopg.rows import dict_row


#Carregar variáveis de ambiente (Segurança)
load_dotenv()

#Preencher variáveis
USER_DB = os.environ.get("DB_USER")
PASS_DB = os.environ.get("DB_PASS")
NAME_DB = os.environ.get("DB_NAME")
HOST_DB = os.environ.get("DB_HOST")

##
## Configurar a base de dados
##


def db_connection():
    db = psycopg.connect(
        user= USER_DB,
        password= PASS_DB,
        port='5432',
        host = HOST_DB,
        dbname= NAME_DB,
        row_factory=dict_row
    )
    
    db.autocommit = False #Desativar autocommit para evitar problemas
    

    return db


