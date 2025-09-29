"""
Local development settings.
This file contains settings specific to local development environment.
"""

import socket
from .base import *

# -----------------------------------------------------------------------------
# DEBUG CONFIGURATION
# -----------------------------------------------------------------------------
DEBUG = True
ALLOWED_HOSTS = ['*']

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION (Local Development)
# -----------------------------------------------------------------------------
if 'RDS_DB_NAME' in env:
    # AWS RDS or cloud database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env("RDS_DB_NAME"),
            'USER': env("RDS_DB_USER"),
            'PASSWORD': env("RDS_DB_PASSWORD"),
            'HOST': env("RDS_DB_HOST", default=env("HOST", default="localhost")),
            'PORT': env("RDS_DB_PORT", default=env("PORT", default='5432')),
        }
    }
elif 'LOCAL_DB' in env:
    # Local PostgreSQL development DB
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env("LOCAL_DB_NAME"),
            'USER': env("LOCAL_DB_USER", default="postgres"),
            'PASSWORD': env("LOCAL_DB_PASSWORD"),
            'HOST': env('LOCAL_DB_HOST', default='localhost'),
            'PORT': env('LOCAL_DB_PORT', default='5432'),
        }
    }

# If you prefer PostgreSQL for local development, uncomment below:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': env("LOCAL_DB_NAME", default="your_local_db"),
#         'USER': env("LOCAL_DB_USER", default="postgres"),
#         'PASSWORD': env("LOCAL_DB_PASSWORD", default=""),
#         'HOST': env('LOCAL_DB_HOST', default='localhost'),
#         'PORT': env('LOCAL_DB_PORT', default='5432'),
#     }
# }

# -----------------------------------------------------------------------------
# CORS CONFIGURATION (Permissive for local development)
# -----------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:4200',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:4200',
]

CORS_ALLOW_HEADERS = [
    'Accept',
    'Accept-Encoding',
    'Authorization',
    'Content-Type',
    'DNT',
    'Origin',
    'User-Agent',
    'X-CSRFToken',
    'X-Requested-With',
    'Access-Control-Allow-Origin',
    'X-Language-Code',
]

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://localhost:\d+$",
    r"^https?://127\.0\.0\.1:\d+$",
]

# -----------------------------------------------------------------------------
# DEBUG TOOLBAR CONFIGURATION
# -----------------------------------------------------------------------------
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Allow Docker-based IPs to access the debug toolbar
INTERNAL_IPS = ['127.0.0.1', '172.17.0.1']
try:
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [ip[:ip.rfind('.')] + '.1' for ip in ips]
except Exception as e:
    print(f"[Warning] Could not determine INTERNAL_IPS: {e}")

# -----------------------------------------------------------------------------
# EMAIL CONFIGURATION (Console backend for local development)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# -----------------------------------------------------------------------------
# LOGGING CONFIGURATION
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}