import os
from logging.config import dictConfig
import logging

try:
    BASE_DIR = os.getcwd()
    print(BASE_DIR)
    LOG_DIR = os.path.join(BASE_DIR, 'logs')

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'verbose': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s - %(lineno)d - %(message)s'
            },
            'verbose_moodys_ml': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s - %(lineno)d - %(id)d - %(message)s'
            },
            'frontend': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'verbose',
            },
            'q_f_doc_checker': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'verbose',
                'filename': os.path.join(LOG_DIR, 'q_f_doc_checker.log')
            }
        },
        'loggers': {
            'q_f_doc_checker': {
                'handlers': ['q_f_doc_checker', 'console'],
                'level': 'DEBUG',
                'propagate': True,
            }
        },
    }

    dictConfig(LOGGING)
    logger = logging.getLogger('q_f_doc_checker')
except Exception as e:
    pass