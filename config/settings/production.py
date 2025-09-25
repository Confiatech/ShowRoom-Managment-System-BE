"""
Production environment settings.
This file contains settings for production environment with security and performance optimizations.
"""

from .base import *

# -----------------------------------------------------------------------------
# SECURITY CONFIGURATION
# -----------------------------------------------------------------------------
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF security
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION (Production)
# -----------------------------------------------------------------------------
if 'RDS_DB_NAME' in env:
    # AWS RDS or cloud database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': env("RDS_DB_NAME"),
            'USER': env("RDS_DB_USER"),
            'PASSWORD': env("RDS_DB_PASSWORD"),
            'HOST': env("RDS_DB_HOST"),
            'PORT': env("RDS_DB_PORT", default='5432'),
            'OPTIONS': {
                'sslmode': 'require',
            },
            'CONN_MAX_AGE': 60,
        }
    }
else:
    raise ValueError("Production database configuration missing. Please set RDS_DB_* environment variables.")

# -----------------------------------------------------------------------------
# CORS CONFIGURATION (Restrictive for production)
# -----------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

CORS_ALLOW_HEADERS = [
    'Accept',
    'Accept-Encoding',
    'Authorization',
    'Content-Type',
    'Origin',
    'User-Agent',
    'X-CSRFToken',
    'X-Requested-With',
]

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)

# -----------------------------------------------------------------------------
# STATIC & MEDIA FILES (Production with AWS S3 or similar)
# -----------------------------------------------------------------------------
# Uncomment and configure for AWS S3 or similar cloud storage
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
# AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
# AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
# AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
# AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
# AWS_DEFAULT_ACL = None
# AWS_S3_OBJECT_PARAMETERS = {
#     'CacheControl': 'max-age=86400',
# }

# -----------------------------------------------------------------------------
# EMAIL CONFIGURATION (Production)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

# -----------------------------------------------------------------------------
# CACHING CONFIGURATION (Production with Redis)
# -----------------------------------------------------------------------------
# Uncomment and configure for Redis caching
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# -----------------------------------------------------------------------------
# LOGGING CONFIGURATION (Production)
# -----------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# -----------------------------------------------------------------------------
# PERFORMANCE OPTIMIZATIONS
# -----------------------------------------------------------------------------
# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60

# Template caching
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]