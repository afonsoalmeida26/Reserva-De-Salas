import jwt #encriptação
from app.db import db_connection
from flask import Blueprint, jsonify, request, Flask, make_response
from app import StatusCodesAPI
import datetime
import psycopg
from argon2 import PasswordHasher
from dotenv import load_dotenv
import os
from argon2.exceptions import VerifyMismatchError
from email_validator import validate_email, EmailNotValidError
from app import get_token_info

auth_bp = Blueprint("auth", __name__, url_prefix="/aluno")

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
ph = PasswordHasher()



###
### FUNÇÃO PARA DEVOLVER OS DADOS DO UTILIZADOR ATUAL (A PARTIR DO COOKIE)
###
@auth_bp.route('/me', methods=['GET'])
def me():

    token = request.cookies.get('token')

    if token is None:
        response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Sessão expirada'}
        return jsonify(response), response['Status']

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms="HS256")
    except jwt.ExpiredSignatureError:
        response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Sessão expirada'}
        return jsonify(response), response['Status']
    except jwt.InvalidTokenError:
        response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Token inválido'}
        return jsonify(response), response['Status']

    response = {
        'Status': StatusCodesAPI['success'],
        'Result': {
            'nome': payload.get('nome'),
            'id_pessoa': payload.get('id_pessoa'),
            'tipo': payload.get('tipo'),
        }
    }
    return jsonify(response), response['Status']




###
### FUNÇÃO PARA CRIAR NOVO ALUNO
###
@auth_bp.route('/novo', methods = ['PUT'])
def criar_aluno():

    #Obter dados vindos do utilizador em JSON
    data = request.get_json()
    
    
    #Validação de dados
    if not "nome" in data or not "password" in data or not "email" in data or not "data_nasc" in data:
        response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Lack of Data'}
        return jsonify(response), response['Status']
    
    
    nome = data["nome"]
    password = ph.hash(data["password"])
    email = data["email"]
    data_nasc = data["data_nasc"]
    tipo = "aluno"
    
    #VALIDAÇÃO DE DADOS VINDAS DO UTILIZADOR
    if(len(nome) < 8):
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Nome Completo: Pelo menos 8 caracteres'}
        return jsonify(response), response["Status"]

    
    
    elif (len(password) < 10):
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Palavra-Passe: Pelo menos 10 caracteres'}
        return jsonify(response), response["Status"]

    #validar email
    try:
        email_info = validate_email(email, check_deliverability=True)
        
        email = email_info.normalized
    except EmailNotValidError as enve:
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': str(enve)}
        
        return jsonify(response), response["Status"]
    
    
    #Converter para datetime para introduzir na DB
    data_nasc_datetime = datetime.datetime.strptime(data_nasc, "%Y-%m-%d")
    
    conn = None
    cursor = None
    
    
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        
        query = '''
        INSERT INTO Pessoa (nome, data_nasc, email, password, tipo)
        VALUES(%s, %s, %s, %s, %s)
        RETURNING id
        '''
        values = (nome, data_nasc_datetime, email, password, tipo)
        
        cursor.execute(query, values)
        
        id_aluno = cursor.fetchone()["id"]
            
        print("Utilizador criado com sucesso. A retorna token de autenticação")
        
        
        query_aluno = '''
        
            INSERT INTO Aluno (pessoa_id)
            VALUES (%s)
        '''
        
        values_aluno = (id_aluno,)
        
        cursor.execute(query_aluno, values_aluno)
        
            
        payload = {
                
            "id_pessoa": id_aluno,
            "nome" : nome,
            "tipo": tipo
                
        } 
            
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            
        #USADO EM POSTMAN    
        #response = {'Status': StatusCodesAPI['success'], 'Result': 'Conta criada com sucesso', 'Token': token}
        
        response = make_response(jsonify({
            
            'Status': StatusCodesAPI['success'],
            'Result': 'Conta criada com sucesso'
        }))
        
        response.set_cookie(
            'token', #NOME DO COOKIE
            token, #TOKEN
            httponly=True, #IMPEDE ACESSO VIA JAVASCRIPT (XSS)
            samesite='Lax', #PERMITE ENVIO DO COOKIE EM AMBIENTE LOCAL
            secure= False #POR ENQUANTO FALSO
        )
        
        
        #GUARDAR PERMANENTEMENTE AS ALTERAÇÕES NA DB
        if(conn):
            conn.commit()
            
        #USADO EM POSTMAN
        #return jsonify(response)
        
        return response, StatusCodesAPI['success']

        
    except (psycopg.DatabaseError) as e:
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': str(e)}
        
        
        #CANCELAR TRANSAÇÃO, MANTER AS PROPRIEDADES ACID
        if(conn):  
            conn.rollback()
        
        return jsonify(response), response['Status']
            
    
    finally:
        if (cursor is not None):
            cursor.close()
        if(conn is not None):
            conn.close()


###
### FUNÇÃO PARA FAZER LOGIN DO ALUNO
###

@auth_bp.route('/login', methods = ['POST'])
def login_aluno():
    
    
    data = request.get_json() #Dados vindos do utilizador para login
    
    if(not "email" in data or not "password" in data):
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Missing email or password. Try again'}
        return jsonify(response), StatusCodesAPI['api_error']
    
    
    email = data["email"]
    password = data["password"]
    
    conn = None
    cur = None
    
    try:
        
        conn = db_connection()
        cur = conn.cursor()
        
        query = '''
            SELECT id, nome, password, tipo
            FROM Pessoa
            WHERE email = %s
            FOR SHARE
        '''
        values = (email,)
        
        cur.execute(query, values)
        
        resultado = cur.fetchone()#É utilizada a classe dict_row para o fetchone retorna um dicionário e facilitar
        
        #CASO NÃO ENCONTRE UTILIZADOR
        if(resultado is None):
            response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Utilizador não encontrado'}
            
            if(conn):
                conn.rollback()
            
            return jsonify(response), StatusCodesAPI['api_error']

        
        #CASO ENCONTRE
        id_user = resultado["id"]
        nome = resultado["nome"]
        password_hash = resultado["password"]
        tipo = resultado["tipo"]

        try:
            ph.verify(password_hash, password)
        #PASSE ESTEJA INCORRETA    
        except (Exception, VerifyMismatchError) as vme:
            response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Palavra Passe incorreta'}
            
            if(conn):
                conn.rollback()

            return jsonify(response), 401  
            
        print("Utilizador encontrado")
                
        payload = {
                    
            "nome": nome,
            "id_pessoa": id_user,
            "tipo": tipo
                    
        }
                
                
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
                
                
        #POSTMAN
        #response = {'Status': StatusCodesAPI['success'], 'Result': 'Utilizador logado com sucesso', 'Token' : token}

        response = make_response(jsonify({
                
            'Status': StatusCodesAPI['success'],
            'Result': 'Login efetuado com sucesso'
        }))
            
        response.set_cookie(
            'token', #NOME DO COOKIE
            token, #TOKEN
            httponly=True, #IMPEDE ACESSO VIA JAVASCRIPT (XSS)
            samesite='Lax', #PERMITE ENVIO DO COOKIE EM AMBIENTE LOCAL
            secure= False #POR ENQUANTO FALSO
        )
        
        if(conn):
            conn.commit()
                    
        return response, StatusCodesAPI['success']
            
        #POSTMAN
        #return jsonify(response)    
          
            
    except (psycopg.DatabaseError) as e:
        
        if(conn):
            conn.rollback()
            
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': str(e)}
        return jsonify(response), 401

    
    finally:
        if(cur is not None):
            cur.close()
        if(conn is not None):
            conn.close()



@auth_bp.route('/logout', methods = ['POST'])
def logout():
    
    
    response = make_response(jsonify({
            
        'Status': StatusCodesAPI['success'],
        'Result': 'Conta criada com sucesso'
    }))
        
    response.set_cookie(
        'token', #NOME DO COOKIE
        "", #TOKEN
        expires=0, #APAGAR O COOKIE IMEDIATAMENTE
        httponly=True,
        samesite='Lax'
    )

    return response, 200
    
###
### FUNÇÃO PARA ALTERAR SENHA DO ALUNO
###



@auth_bp.route('/change_password', methods = ["PUT"])
def change_pass():

    #POSTMAN
    #token = request.headers.get("Authorization")
    
    token = request.cookies.get("token")
    
    #Caso nenhum token seja enviado
    if not token:
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Sessão expirada'}
        return jsonify(response)

    try:
        #Nome e número de estudante correspondente ao token enviado
        nome, id_user = get_token_info(token)
    except Exception:
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Token inválido'}
        return jsonify(response)
    
    #Buscar nova password enviada
    
    data = request.get_json()
    
    if not data:
        response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'No data sent'}
        return jsonify(response)
    
    new_pass = data["password"]
    
    conn = None
    cur = None
    
    try:
        
        conn = db_connection()
        cur = conn.cursor()
        
        #QUERY PARA VERIFICAR SE EXISTE PESSOA
        query = '''

            SELECT id, password
            FROM Pessoa
            Where id = %s
            FOR UPDATE
        
        '''
        
        values = (id_user,)
        
        cur.execute(query, values)
        
        data_query = cur.fetchone()
        
        
        #Estudante com numero de estudante tal não existe
        if(data_query is None):
            response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Account not founded'}
            
            if(conn):
                conn.rollback()

            return jsonify(response)
    
        
        old_pass = data_query["password"]
        
        try:
            #VERIFICAÇÃO PARA EVITAR ALTERAR A PASSE PARA A MESMA
            ph.verify(old_pass, new_pass)

            #Avança já as passes sejam iguais
            same_pass = True
                
        except (VerifyMismatchError) as e_hash:
            same_pass = False
            
        #Mesma passe    
        if same_pass:
            response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Same Password. Try a new one'}
            #Libertar lock do registo
            if(conn):
                conn.rollback()
                
            return jsonify(response)    
        
        #ATUALIZAR PASSE CASO ESTA SEJA DIFERENTE DA ANTERIOR
        else:
                
            new_pass_hash = ph.hash(new_pass)
                    
            query_new_pass = '''
                    
                UPDATE Pessoa
                SET password = %s
                WHERE id  = %s
                    
            '''
                    
                    
            values_new_pass = (new_pass_hash, id_user)
                    
            cur.execute(query_new_pass, values_new_pass)
                    
            if(conn):
                conn.commit()
                    
                    
            response = {'Status': StatusCodesAPI['success'], 'Result': 'Password change successful'}
            
            return jsonify(response)
   
    except (psycopg.DatabaseError) as e:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(e)}
        
        #Caso haja algum problema, faça rollback
        if(conn):
            conn.rollback()
        
        
        return jsonify(response)
    
    
    finally:
        if(cur):
            cur.close()
        
        if(conn):
            conn.close()
        
    
    
    