import os
import sys
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(BASE_DIR))
SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxgt'

DEBUG = False
ALLOWED_HOSTS = ["*"]
INSTALLED_APPS = [
    "testnet_ranking",
    "dashboard",
    "calculator",
]

MIDDLEWARE = [
    'explorer_s_common.middleware.ResponseMiddleware',
]

ROOT_URLCONF = 'explorer_s_activity.urls'
WSGI_APPLICATION = 'explorer_s_activity.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'explorer_s_activity',
        'USER': os.getenv("MYSQL_ROOT"),
        'PASSWORD': os.getenv("MYSQL_PASSWORD"),
        'HOST': os.getenv("MYSQL_HOST"),
        'PORT': os.getenv("MYSQL_PORT"),
        'CONN_MAX_AGE': 300,
        'OPTIONS': {'charset': 'utf8mb4'},
        'TEST': {
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_general_ci',
        }
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
USE_TZ = False
STATIC_URL = '/static/'
logging.basicConfig(format='%(levelname)s:%(asctime)s %(pathname)s--%(funcName)s--line %(lineno)d-----%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.WARNING)
