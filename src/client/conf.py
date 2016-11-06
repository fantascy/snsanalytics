import datetime


"""
Standard user and admin user configurations.
"""
DEFAULT_PASSWD = "gt10gt10"
USER_EMAIL = "bryan.springer.snsa@gmail.com"
USER_PASSWD = "gt10gt10"
ADMIN_USER = "qa07.sa@gmail.com"
ADMIN_PASSWD = "gt10gt10"


"""
Server configurations.
"""
APPLICATION_ID = 'localhost'
IS_DEV_SERVER = APPLICATION_ID == 'localhost'
BACKEND = None #'b4'
SERVER_DOMAIN = None #"localhost.snsanalytics.com:8080"


"""
If True, use prepared Twitter API token pool.
"""
USE_TOKEN_POOL = False


def is_client():
    return not os.environ.has_key('SERVER_SOFTWARE')


def cwd(): 
    return os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))


import logging
import os, sys


LOG_DIR = os.path.join(cwd(), 'log')


def is_debug():
    try:
        return eval(os.environ.get('SNS_DEBUG', 'False'))
    except:
        return False
    

def _config_logging():
    debug = is_debug()
    
    class NoStackTraceFormatter(logging.Formatter):
        def format(self, record):
            record.exc_info = None
            record.exc_text = None
            return logging.Formatter.format(self, record)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # set up file logger
    try:
        if not os.path.exists(LOG_DIR):
            os.mkdir(LOG_DIR)
        file_path = os.path.join(LOG_DIR, "%s-%s-%d.log" % (os.path.basename(os.path.splitext(sys.argv[0])[0]), datetime.datetime.now().strftime("%Y%m%d%H%M%S"), os.getpid()))
        file_handler = logging.FileHandler(file_path)
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except IOError, e:
        if e.errno == 13:
            print 'could not create log file: ', e
        else:
            raise

    # set up console logger
    console = logging.StreamHandler()
    fmt = '%(message)s'
    console.setFormatter(logging.Formatter(fmt))
    if not debug:
        console.setFormatter(NoStackTraceFormatter(fmt))
    logger.addHandler(console)
    return logger


if is_client(): _config_logging()

