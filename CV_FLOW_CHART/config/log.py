import os
from logging.config import dictConfig
import logging

BASE_DIR = os.getcwd()
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
        'verbose_cv': {
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
        'flowchartlog': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filename': os.path.join(BASE_DIR, 'logs/flowchartlog.log')
        }
    },
    'loggers': {
        'cvdocs': {
            'handlers': ['flowchartlog', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    },
}

dictConfig(LOGGING)
logger = logging.getLogger('cvdocs')
