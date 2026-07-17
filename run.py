import logging
from app import app #App - Flask
import os


#Função Main

if __name__ == "__main__":
    
    logging.basicConfig(filename='log_file.log')
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s', '%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    host = '0.0.0.0'
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f'API v1.0 online: http://{host}:{port}')
    app.run(host=host, debug=True, threaded=True, port=port)