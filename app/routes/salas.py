from app.db import db_connection
from flask import Blueprint, jsonify, request
import jwt
import psycopg
from datetime import datetime
from app import StatusCodesAPI
from app import get_token_info


salas_bp = Blueprint("salas", __name__, url_prefix="/sala")







###
### FUNÇÃO PARA ADMININSTRADORES CRIAREM UMA NOVA SALA
###

@salas_bp.route('/nova_sala/<n_sala>', methods = ['POST'])
def criar_sala(n_sala):
    
    #Resgatar token para verificar se é admin
    token = request.cookies.get("token")
    
    try:
        
        if(token is None):
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'No token sent'}
            return jsonify(response)
        
        
        nome, id_user, tipo = get_token_info(token)
        
        #VERIFICAÇÃO PARA APENAS ADMIN
        if(tipo != "admin"):
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'No permission'}

            return jsonify(response), response['Status']

        
        #CASO SEJA ADMIN
        
        conn = None
        cur = None
        
        try:
            
            conn = db_connection()
            cur = conn.cursor()
            
            #QUERY PARA INSERIR NOVA SALA
            query_new_room = '''
                INSERT INTO sala(numero_sala)
                VALUES (%s)
                RETURNING id_sala
            '''
            
            values_new_room = (n_sala,)
            
            
            cur.execute(query_new_room, values_new_room)
            
            data_new_room = cur.fetchone()
            
            if(data_new_room is None):
                response = {'Status': StatusCodesAPI['internal_error'], 'Errors': 'Error creating new room. Try again'}
            
                return jsonify(response), response['Status']

            
            
            id_sala = data_new_room["id_sala"]
            
            if(conn):
                conn.commit()
            
            response = {'Status': StatusCodesAPI['success'], 'Result': 'Sala criada com sucesso', 'ID SALA': id_sala}
            
            return jsonify(response), response['Status']
                
        #CHAVE DUPLICADA (SALA JÁ EXISTE)
        except psycopg.errors.UniqueViolation as uv:
            response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Sala já existe. Tente outra'}
            
            #Caso ocorra algum problema, faz rollback
            if(conn):
                conn.rollback()
            
            
            return jsonify(response), response['Status']
        
        #NÚMERO DE SALA INVÁLIDO
        
        except psycopg.DataError as de:
            response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Número de sala inválido'}
            
            #Caso ocorra algum problema, faz rollback
            if(conn):
                conn.rollback()
            
            
            return jsonify(response), response['Status']
        
        
        except (psycopg.DatabaseError) as dbe:
            
            msg = str(dbe).split("\n")[0].strip()
            
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': msg}
            
            #Caso ocorra algum problema, faz rollback
            if(conn):
                conn.rollback()
            
            
            return jsonify(response), response['Status']
            
        except (Exception) as e:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(e)}
            
            #Caso ocorra algum problema, faz rollback
            if(conn):
                conn.rollback()
            
            
            return jsonify(response),response['Status']
            
        finally:
            if(cur):
                cur.close()
            if(conn):
                conn.close()
        
    
    except jwt.InvalidTokenError as e:
        
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(e)}
        
        return jsonify(response),response['Status']
        
    except jwt.ExpiredSignatureError as ese:
        
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ese)}
        
        return jsonify(response), response['Status']




###
### FUNÇÃO PARA APAGAR UMA SALA (ADMININSTRADORES)
###
@salas_bp.route('/remover_sala/<n_sala>', methods = ['DELETE'])
def remover_sala(n_sala):
    
    
    try:
        #obter token do utilizador
        token = request.cookies.get("token")
        
        if(token is None):
            response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'Token vazio'}
            
            return jsonify(response), response['Status']
        
        
        nome, id_user, tipo = get_token_info(token)
        
        
        #Caso não seja admin
        if(tipo != "admin"):
            response = {'Status': StatusCodesAPI['api_error'], 'Result': 'Utilizador não tem permissões para remover uma sala'}
            
            return jsonify(response), response['Status']
        
        
        conn = None
        cur = None
        
        try:
            
            conn = db_connection()
            cur = conn.cursor()
            
            
            #query para retornar id da sala a remove
            query_id_sala = '''
            
                SELECT id_sala
                FROM Sala
                WHERE numero_sala = %s
                FOR UPDATE
            '''
            
            values_id_sala = (n_sala,)
            
            cur.execute(query_id_sala, values_id_sala)
            
            data = cur.fetchone()
            
  

            #Não encontra nenhuma sala
            if(not data):
                response = {'Status': StatusCodesAPI['api_error'], 'Result': f'Sala com número {n_sala} não encontrada'}
                
                if(conn):
                    conn.rollback()
                
                return jsonify(response), response['Status']
            
            id_sala = data["id_sala"]
            
            
            #verificar se existem reservas associadas a essa sala a remover
            query_reserva = '''
                SELECT r.id_reserva as "ID RESERVA"
                FROM Reserva r
                WHERE r.sala_id_sala = %s
                FOR UPDATE
            '''
            
            values_reserva = (id_sala,)
            
            cur.execute(query_reserva, values_reserva)
            
            
            data_id_reserva = cur.fetchall()
            
            
            #Caso haja reservas associadas a essa sala
            if(data_id_reserva):
                
                #apagar reservas com faltas na tabela Faltas
                for reserva in data_id_reserva:
                    
                    id_reserva = reserva['ID RESERVA']
                    
                    
                    query_remover_faltas = '''
                    
                        DELETE FROM Faltas
                        WHERE reserva_id_reserva = %s
                    
                    
                    '''
                
                    values_remover_faltas = (id_reserva,)
                
                    cur.execute(query_remover_faltas, values_remover_faltas)
                    
                    
                    #apagar check in dessas reservas
                    
                    
                    query_remover_check = '''
                    
                        DELETE FROM Check_in
                        WHERE reserva_id_reserva = %s
                    
                    
                    '''
                    values_remover_check = (id_reserva,)
                    
                    cur.execute(query_remover_check, values_remover_check)
                    
                    
                
                #Apagar reservas associadas a essa sala
                query_remover_reserva = '''
                
                    DELETE FROM Reserva
                    WHERE sala_id_sala = %s
                
                '''
                
                values_remover_sala = (id_sala,)
                
                cur.execute(query_remover_reserva, values_remover_sala)
                
            #Caso não haja reservas associadas a essa sala
            #query para deletar sala
                
            query_deletar_sala = '''
                
                DELETE FROM Sala
                WHERE id_sala = %s
                
            '''
            values_deletar_sala = (id_sala,)
                
            cur.execute(query_deletar_sala, values_deletar_sala)
            
            print(f"Sala {n_sala} removida com sucesso")
            
            
            response = {'Status': StatusCodesAPI['success'], 'Result': f'Sala {n_sala} removida com sucesso'}
            
            if(conn):
                conn.commit()
            
            return jsonify(response), response["Status"]
            
        except psycopg.DatabaseError as dbe:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
            
            if(conn):
                conn.rollback()
            
            return jsonify(response), response['Status']
        finally:
            
            if(cur):
                cur.close()
            if(conn):
                conn.close()
    
    except jwt.InvalidTokenError as ite:
        response = {'Status': StatusCodesAPI['api_error'], 'Errors': str(ite)}
        
        return jsonify(response), response['Status']
    
    except jwt.ExpiredSignatureError as ese:
        response = {'Status': StatusCodesAPI['api_error'], 'Errors': str(ese)}
        
        return jsonify(response), response['Status']




###
### FUNÇÃO PARA MOSTRAR SALAS EXISTENTES
###
@salas_bp.route('/listar_salas', methods = ['GET'])
def listar_salas():
    
    #OBTER TOKEN
    try:
        token = request.cookies.get('token')
        
        
        if(token is None):
            response = {'Status': StatusCodesAPI['api_error'], 'Errors': 'TOKEN NOT FOUNDED'}
            
            return jsonify(response), 500

        #OBTER INFORMAÇÕES DO TOKEN
        nome, id_user, tipo = get_token_info(token)
        
        
        conn = None
        cur = None
        
        try:
            #ABRIR CONEXÃO COM DB
            
            conn = db_connection()
            cur = conn.cursor()
            
            query_salas = '''

                SELECT numero_sala, id_sala
                FROM Sala 
                ORDER BY numero_sala ASC
                FOR SHARE
            '''
            
            cur.execute(query_salas,)
            
            data_salas = cur.fetchall()
            
            if(not data_salas):
                response = {'Status': StatusCodesAPI['success'], 'Results': 'Nenhuma sala encontrada'}
                
                if(conn):
                    conn.rollback()
                    
                return jsonify(response), 200
            
            lista_sala = []
            
            
            
            
            for sala in data_salas:
 
                
                result = {
                    
                    'id_sala': sala["id_sala"],
                    'numero_sala': sala["numero_sala"]
                    
                }
                
                lista_sala.append(result)
            

            response = {'Status': StatusCodesAPI['success'], 'Results': lista_sala}
            
            if(conn):
                conn.commit()
                

            return jsonify(response), 200
            
            

        except psycopg.DatabaseError as dbe:
            response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
            
            if(conn):
                conn.rollback()
            
            return jsonify(response), 401
        
        finally:
            if(cur):
                cur.close()
            
            if(conn):
                conn.close()
        
        
    
    except jwt.InvalidTokenError as ite:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ite)}
        
        return jsonify(response), 401
    
    except jwt.InvalidSignatureError as ise:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(ise)}
        
        return jsonify(response), 401