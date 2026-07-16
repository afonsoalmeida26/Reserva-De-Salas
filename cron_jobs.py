from app import db_connection
from app import StatusCodesAPI
import psycopg

###
### FUNÇÃO PARA COLOCAR RESERVAS A DECORREREM
### ESTADO - CHECK-IN && DATA,HORA ATUAL ENTRE O INICIO E FIM DA RESERVA
def atualizar_reserva():
    
    
    conn = None
    cur = None
    
    try:
        
        conn = db_connection()
        cur = conn.cursor()
        
        #QUERY para atualizar estado de reserva
        query_atualizar = '''
        
            UPDATE Reserva
            SET estado = 'A decorrer'
            WHERE estado = 'Check-In feito' AND CURRENT_TIMESTAMP BETWEEN inicio_reserva AND fim_reserva

        '''
        
        cur.execute(query_atualizar,)
        
        n_registos = cur.rowcount

        response = {'Status': StatusCodesAPI['success'], 'Result':f'{n_registos} reserva(s) atualizada(s)!'}
        
        
        if(conn):
            conn.commit()
            
            
        print(response)
        
    
    except psycopg.DatabaseError as dbe:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
        
        if(conn):
            conn.rollback()
        
        
        print(response)
    
    except Exception as e:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(e)}
        
        if(conn):
            conn.rollback()
        
        
        print(response)

    finally:
        
        if(cur):
            cur.close()
        
        if(conn):
            conn.close()
            



###
### FUNÇÃO PARA FAZER VERIFICAÇÃO DE FALTAS NAS RESERVAS
###

def verificar_faltas():
    
    
    conn = None
    cur = None
    
    
    #CONTADOR DE RESERVAS ATRASADAS
    count = 0
    
    try:
        conn = db_connection()
        cur = conn.cursor()
        
        #QUERY PARA VERIFICAR RESERVAS QUE EXCEDAM 15 MINUTOS E NÃO TENHAM CHECK IN
        query_verificar = '''
        
            SELECT r.id_reserva as "ID RESERVA", r.estado as "ESTADO", r.aluno_pessoa_id as "ID ALUNO"
            FROM Reserva r
            WHERE CURRENT_TIMESTAMP > r.inicio_reserva + INTERVAL '15 MINUTE'
            AND r.estado = 'Confirmado'
            ORDER BY r.inicio_reserva ASC
            FOR UPDATE;
        '''
        
        cur.execute(query_verificar)
        
        data_reservas = cur.fetchall()
        
        #Caso não haja reservas atrasadas
        if(data_reservas is None):
            response = {'Status': StatusCodesAPI['sucess'], 'Results': 'Nenhuma reserva atrasada'}
                    
            print(response)
        
        for reserva in data_reservas:
            
            #BUSCAR DADOS DE CADA RESERVA
            id_reserva = reserva["ID RESERVA"]
            estado = reserva["ESTADO"]
            id_user = reserva["ID ALUNO"]

            
            #INSERIR REGISTO DE FALTAS 
            query_faltas = '''
            
                INSERT INTO Faltas (falta, reserva_id_reserva)
                VALUES (%s, %s)
            '''
            
            values_faltas = ('True', id_reserva)
            
            cur.execute(query_faltas, values_faltas)
            
            #ATUALIZAR ESTADO DA RESERVA ATRASADA
            
            query_estado = '''
            
                UPDATE Reserva SET estado = 'Cancelado' WHERE id_reserva = %s
            
            '''
            
            values_estado = (id_reserva,)
            
            
            cur.execute(query_estado, values_estado)
            
            count+=1
            
            
        response = {'Status': StatusCodesAPI['success'], 'Results': f'{count} reserva(s) atrasada(s)'}
        
        
        #GUARDAR PERMANENTEMENTE AS ALTERAÇÕES NA DB
        if(conn):
            conn.commit()
        
        
        print(response)   
            

        
    except psycopg.DatabaseError as dbe:
        response = {'Status': StatusCodesAPI['internal_error'], 'Errors': str(dbe)}
        
        if(conn):
            conn.rollback()
        
        
        print(response)
    
    finally:
        
        if(cur):
            cur.close()
        
        if(conn):
            conn.close()



if __name__ == "__main__":
    print("A INICIALIZAR VERIFICAÇÕES")
    
    atualizar_reserva()
    verificar_faltas()
    
    print("VERIFICAÇÕES CONCLUÍDAS")