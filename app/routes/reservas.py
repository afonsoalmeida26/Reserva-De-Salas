from app.db import db_connection
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
import os
import jwt
from app import StatusCodesAPI
import psycopg
from datetime import datetime

#Criar blueprint de reservas
reservas_bp = Blueprint("reservas", __name__, url_prefix='/reserva')

#Carregar variáveis de ambiente para o sistema
load_dotenv()

#Carregar variável da chave secreta de token
SECRET_KEY = os.environ.get("SECRET_KEY")


###
### FUNÇÃO PARA RETORNAR TOKEN FORNECIDO NO HEADER 'AUTHORIZATION'
###
def get_token_info(token):

    
    payload = jwt.decode(token, SECRET_KEY, algorithms="HS256")
    
    nome = payload["nome"]
    id_pessoa = payload["id_pessoa"]
    tipo = payload["tipo"]
    
    return nome, id_pessoa, tipo




###
### FUNÇÃO PARA CRIAR UM RESERVA (RESERVAR UMA SALA)
###
### AO SER INSERIDO UM REGISTO NA TABELA Reserva, UM TRIGGER DO TIPO BEFORE INSERT, VERIFICA SE A SALA ESTÁ OCUPADA E SE AS HORAS E DATA SÃO VÁLIDAS
###


@reservas_bp.route("/<n_sala>", methods = ["POST"])
def reservar_sala(n_sala):
    
    
    try:
        
        ##Buscar token do utilizador
        #token = request.headers.get("Authorization")
        
        token = request.cookies.get('token')
        
        #Caso não haja nenhum token no cabeçalho
        if(token is None):
            response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Token not sent'}
            return jsonify(response)

        nome, id_user, tipo = get_token_info(token)
        
        
        #Caso não seja um aluno
        if(tipo != 'aluno'):
            response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Apenas alunos'}
            
            return jsonify(response)

        
        #Retornar dados enviados em json pelo utilizador
        data = request.get_json()
        
        #Validação dos dados recebidos
        if('hora_inicio' not in data or 'hora_fim' not in data or 'data_reserva' not in data):
            response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Missing data'}
            return jsonify(response)

        hora_inicio = data['hora_inicio']
        hora_fim = data['hora_fim']
        data_reserva = data['data_reserva']

           

        conn = None
        cur = None
        
        #Converter hora de inicio/fim e data_reserva em timestamp para ser aceite na DB
        
        hora_inicio_ts = (datetime.strptime(hora_inicio, '%H:%M')).time()
        hora_fim_ts = (datetime.strptime(hora_fim, '%H:%M')).time()
        data_reserva_ts = datetime.strptime(data_reserva, '%d-%m-%Y')
        
        data_hora_inicio = datetime.combine(data_reserva_ts, hora_inicio_ts)
        data_hora_fim = datetime.combine(data_reserva_ts, hora_fim_ts)
        
        try:
            
            conn = db_connection()
            cur = conn.cursor()
           
            #Não encontra aluno
            if(id_user is None):
                response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Aluno não existe'}
                return jsonify(response)
            
            #BUSCAR ID DA SALA
            query_id_sala = '''
            
            
                SELECT id_sala
                FROM Sala
                WHERE numero_sala = %s
                FOR SHARE
            '''
            
            values_id_sala = (n_sala,)
            
            cur.execute(query_id_sala, values_id_sala)
            
            data_id_sala = cur.fetchone()
            
            if(data_id_sala is None):
                response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Sala não encontrada'}
                return jsonify(response)
            
            id_sala = data_id_sala["id_sala"]
            
            
            #QUERY PARA EFETUAR RESERVA (TRIGGER SERÁ ATIVADO PARA VALIDAÇÃO DE DADOS E VERIFICAR SE SALA ESTÁ LIVRE)
            query_reserva = '''

                INSERT INTO reserva (inicio_reserva, fim_reserva, estado, aluno_pessoa_id, sala_id_sala )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_reserva
            
            '''
            
            
            values_reserva = (data_hora_inicio, data_hora_fim, 'Confirmado', id_user, id_sala)
            
            cur.execute(query_reserva, values_reserva)
            
            data_id = cur.fetchone()
            
            
            
            #VERIFICAÇÃO DE RESERVA
            if(data_id is None):
                response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'Erro ao inserir reserva. Tente novamente'}
                
                if(conn):
                    conn.rollback()
                    
                return jsonify(response)
            
            
            
            id_reserva = data_id["id_reserva"]
            
            #Foi criada a reserva com sucesso
            response = {
                'Status': StatusCodesAPI['success'], 
                'Result': f'Sala {n_sala} reservada com sucesso. Dia {data_reserva} {hora_inicio} - {hora_fim}', 
                'ID RESERVA': id_reserva
            }
            
            
            #GUARDAR PERMANENTEMENTE NA BADE DE DADOS
            if(conn):
                conn.commit()
            
            
            return jsonify(response), 200
        
        except psycopg.errors.RaiseException as e:
            
            
            erro = str(e).split("\n")[0].strip()
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': erro}
            
            #Caso ocorra algum problema, faz rollback
            if(conn):
                conn.rollback()
            
            return jsonify(response), 400
 
        except (psycopg.DatabaseError) as dbe:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
            
            #Caso ocorra algum problema, faz rollback
            if(conn):
                conn.rollback()
            
            return jsonify(response), 400


        finally:
            if(cur):
                cur.close()
            if(conn):
                conn.close()
        
        
    #Token expirado
    except jwt.ExpiredSignatureError as ese:
        response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Expired Token', 'Errors': str(ese)}
        return jsonify(response)

    except jwt.InvalidTokenError as e:
        
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(e)}
        
        return jsonify(response)
            






###
### FUNÇÃO PARA LISTAR RESERVAS DOS PRÓXIMOS 30 DIAS (Alunos)
###
@reservas_bp.route('/listar_reservas', methods = ['GET'])
def listar_reservas():
    
    
    
    token = request.cookies.get('token')
    
    try:
        
        
        #Caso não haja token no cabeçalho
        if(token is None):
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'Header com token vazio'}
            
            return jsonify(response)
        
        #Obter dados do token
        nome, id_user, tipo = get_token_info(token)
        
        
        #VALIDAÇÃO DE DADOS (Tipo do utilizador)
        if(tipo != 'admin' and tipo != 'aluno'):
            
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'User Type Unknown'}
            return jsonify(response)
        
        
        conn = None
        cur = None
        
        #Abrir conexão com base de dados
        try:
            
            conn = db_connection()
            cur = conn.cursor()
            
            query_reservas = '''
            
                SELECT r.inicio_reserva as "Inicio Reserva", r.fim_reserva as "Fim Reserva", r.estado as "Estado", s.numero_sala as "Número da Sala", r.id_reserva as "ID RESERVA"
                FROM Reserva r
                JOIN Sala s ON r.sala_id_sala = s.id_sala
                WHERE CURRENT_TIMESTAMP < r.inicio_reserva + INTERVAL '30 DAYS'
                AND r.aluno_pessoa_id = %s
                ORDER BY r.inicio_reserva ASC
                FOR SHARE of r;
            '''
            values_reservas = (id_user,)
            
            cur.execute(query_reservas, values_reservas)
            
            lista_reservas = []
            
            data = cur.fetchall()
            
            
            
            
            #Não retornar reservas
            if(len(data) == 0):
            
                
                response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'Sem reservas'}
                
                if(conn):
                    conn.rollback()
                
                return jsonify(response)
            
            #Adicionar cada reserva a um array para retornar ao utilizador
            for registos in data:
                
                reserva = {
                    'ID RESERVA': registos["ID RESERVA"],
                    'Inicio Reserva': datetime.strftime(registos["Inicio Reserva"], format='%d-%m-%Y %H:%M'),
                    'Fim Reserva': datetime.strftime(registos["Fim Reserva"], format='%d-%m-%Y %H:%M'),
                    'Estado': registos["Estado"],
                    'Número Sala': registos["Número da Sala"]
                    
                }
                
                lista_reservas.append(reserva)


            response = {'Status': StatusCodesAPI['success'], 'Results': lista_reservas}
            
            
            if(conn):
                conn.commit()
            
            
            return jsonify(response)
            
            
        except psycopg.DatabaseError as dbe:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
            
            
            if(conn):
                conn.rollback()
            
            
            return jsonify(response)
        
        
        finally:
            
            #FECHAR CURSOR E CONEXÃO COM DB
            if(cur):
                cur.close()
            if(conn):
                conn.close()
            
  
    except jwt.ExpiredSignatureError as ese:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ese)}
        
        return jsonify(response)
    
    except jwt.InvalidTokenError as ite:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ite)}
        
        return jsonify(response)














###
### FUNÇÃO PARA FAZER CHECK IN DE RESERVA
###

@reservas_bp.route('/check_in/<id_reserva>', methods = ['PUT'])
def check_in(id_reserva):
    
    #BUSCAR TOKEN DE UTILIZADOR (VERIFICAR SE O UTILIZADOR PERTENCE À RESERVA)
    try:
        
        
        token = request.cookies.get('token')
        
        #TOKEN VAZIO
        if(token is None):
            response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Token not sent'}
            return jsonify(response), 400
        
        
        #obter informações do token
        nome, id_user, tipo = get_token_info(token)
        
        conn = None
        cur = None
        
        try:
        
            conn = db_connection()
            cur = conn.cursor()

            #query para obter id do aluno da reserva, que o utilizador vai fazer check-in (verificar se a reserva pertence ao utilizador)
            # FOR UPDATE - ATUALIZAR FUTURAMENTE ESTADO DA RESERVA
            query_reserva = '''
            
                SELECT r.aluno_pessoa_id as "ALUNO RESERVA"
                FROM Reserva r
                WHERE r.id_reserva = %s
                FOR UPDATE
            '''
            
            values_query = (id_reserva,)
            
            #executar query
            cur.execute(query_reserva, values_query)
            
            #Obter registo resultado da query
            data = cur.fetchone()
            
            #Caso não encontre uma reserva ao id correspondente
            if(not data):
                
                response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Reserva não encontrada'}

                #libertar lock de for update apesar de no caso de não encontrar nada, não dá lock
                if(conn):
                    conn.rollback()
                
                return jsonify(response), 500
            
            
            id_user_reserva = data["ALUNO RESERVA"]
            
            #Verificar se reserva pertence ao utilizador
            if(id_user != id_user_reserva):
                response = {'Status': StatusCodesAPI['internal_error'], 'Result': 'Reserva não pertence ao utilizador'}

                #libertar lock de for update apesar de no caso de não encontrar nada, não dá lock
                if(conn):
                    conn.rollback()
                
                return jsonify(response), 500
            
            
            #caso pertença
            
            query_atualizar_estado = '''
            
                UPDATE Reserva
                SET estado = 'Check-In feito'
                WHERE id_reserva = %s
            '''
            
            values_estado = (id_reserva,)
            
            cur.execute(query_atualizar_estado, values_estado)
            
            
            #Adicionar check-in na tabela Check_in
            
            #data e hora do check in
            data_hora_checkIn = datetime.now()
            
            
            query_check = '''
            
                INSERT INTO Check_in (data_hora_check, reserva_id_reserva)
                VALUES (%s, %s)
                RETURNING id_check
            '''
            
            values_check = (data_hora_checkIn, id_reserva)
            
            cur.execute(query_check, values_check)
            
            data_check = cur.fetchone()
            
            
            #Verificação se fez a inserção corretamente
            if(not data_check):
                response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'Erro ao fazer check-in. Tente novamente'}

                #libertar lock de for update apesar de no caso de não encontrar nada, não dá lock
                if(conn):
                    conn.rollback()
                
                return jsonify(response), 500
            
            
            
            
            id_check_in = data_check["id_check"]
            
            response = {'Status': StatusCodesAPI['success'], 'Result': 'Check-In feito com sucesso!', 'ID CHECK-IN': id_check_in}
            
            #guardar permanentemente as alterações na base de dados
            if(conn):
                conn.commit()
            
            
            return jsonify(response), 200
            
            
        except psycopg.DatabaseError as dbe:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
            
            if(conn):
                conn.rollback()
            
            
            return jsonify(response), 500

        
        except Exception as e:
            
            msg = str(e).split("\n")[0].strip()
            
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': msg}
            
            if(conn):
                conn.rollback()
            
            
            return jsonify(response), 500
        
        
        finally:
            if(cur):
                cur.close()
            if(conn):
                conn.close()
    
    
    
    except jwt.ExpiredSignatureError as ese:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ese)}
        
        return jsonify(response), 500
    
    except jwt.InvalidTokenError as ite:
        
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ite)}
        
        return jsonify(response), 500
    
    
###
### FUNÇÃO PARA UTILIZADOR CANCELAR RESERVA
###

@reservas_bp.route('/cancelar_reserva/<id_reserva>', methods = ['PUT'])
def cancelar_reserva(id_reserva):
    
    try:
        #OBTER TOKEN
        token = request.cookies.get('token')
        
        #TOKEN VAZIO
        if(token is None):
            response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Token invalid'}

            return jsonify(response), response['Status']


        nome, id_user, tipo = get_token_info(token)
        
        
        #ADMIN VAI PODER CANCELAR RESERVAS TAMBÉM
        if(tipo != 'aluno' and tipo != 'admin'):
            response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Permissão desconhecida'}
            
            return jsonify(response), response['Status']
        
        #COLOCAR RESERVA A CANCELADA
        conn = None
        cur = None
        try:
            
            conn = db_connection()
            cur = conn.cursor()
            
            
            #Verificar se a reserva pertence ao aluno que a está a cancelar
            if(tipo == 'aluno'):
                query_verificar = '''
                    SELECT aluno_pessoa_id
                    FROM Reserva
                    WHERE id_reserva = %s
                    FOR UPDATE
                '''
                values_ver = (id_reserva,)
                
                cur.execute(query_verificar, values_ver)

                data = cur.fetchone()
                
                #Verificação de dados
                if(not data):
                    response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Reserva não encontrada'}

                    if(conn):
                        conn.rollback()
                    
                    return jsonify(response), response['Status']
                
                
                id_aluno_reserva = data["aluno_pessoa_id"]

                #Reserva não pertence ao aluno que a está a cancelar
                if(id_aluno_reserva != id_user):
                    response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Reserva não pertence ao aluno'}

                    if(conn):
                        conn.rollback()
                    
                    return jsonify(response), response['Status']
                
                
            
            #query para colocar reserva cancelada (garantir que apenas reservas confirmadas podem ser canceladas)
            query_cancelar = '''
                UPDATE Reserva
                SET estado = 'Cancelado'
                WHERE id_reserva = %s AND estado = 'Confirmado'
            
            '''
            
            values_cancelar = (id_reserva,)
            
            cur.execute(query_cancelar, values_cancelar)
            
            n_reserva = cur.rowcount #número de registos alterados
            
            if(n_reserva == 0):
                response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'Reserva não encontrada ou check-in já feito'}
                
                if(conn):
                    conn.rollback()
                
                return jsonify(response), response['Status']
            
            response = {'Status': StatusCodesAPI['success'], 'Result': 'Reserva cancelada com sucesso'}
            
            #guardar permanentemente as alterações na bd
            if(conn):
                conn.commit()
            
            return jsonify(response), response['Status']
            
            
        except psycopg.DatabaseError as dbe:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}

            #cancelar alterações feitas na bd
            if(conn):
                conn.rollback()
            
            
            return jsonify(response), response['Status']
        
        except Exception as e:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(e)}

            if(conn):
                conn.rollback()

            return jsonify(response), response['Status']
        
        finally:
            
            if(cur):
                cur.close()
            if(conn):
                conn.close()
        
        
    except jwt.ExpiredSignatureError as ese:
        response = {'Status': StatusCodesAPI['api_error'], 'Errors': str(ese)}
        
        return jsonify(response), response['Status']
    
    except jwt.InvalidTokenError as ite:
        response = {'Status': StatusCodesAPI['api_error'], 'Errors': str(ite)}
        return jsonify(response), response['Status']