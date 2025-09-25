"""
Development environment settings.
This file contains settings for development server/staging environment.
"""

from .base import *

# -----------------------------------------------------------------------------
# DEBUG CONFIGURATION
# -----------------------------------------------------------------------------
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=['localhost', '127.0.0.1'])

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION (Development/Staging)
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
else:
    # Fallback to SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# -----------------------------------------------------------------------------
# CORS CONFIGURATION (More restrictive than local)
# -----------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    'http://localhost:4200',
    'https://localhost:4200',
])

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

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)

# -----------------------------------------------------------------------------
# DEBUG TOOLBAR CONFIGURATION (Only if DEBUG is True)
# -----------------------------------------------------------------------------
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']


# -----------------------------------------------------------------------------
# LOGGING CONFIGURATION
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}