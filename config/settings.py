import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file if present
load_dotenv(override=True)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-build-time-key-replace-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# SECURITY WARNING: It's recommended that you use this when
# running in production. The URLs will be known once you first deploy
# to Cloud Run. This code takes the URLs and converts it to both these settings formats.
CLOUDRUN_SERVICE_URLS = os.getenv("CLOUDRUN_SERVICE_URLS", default=None)
if CLOUDRUN_SERVICE_URLS:
    CSRF_TRUSTED_ORIGINS = CLOUDRUN_SERVICE_URLS.split(",")
    # Remove the scheme from URLs for ALLOWED_HOSTS
    ALLOWED_HOSTS = [urlparse(url).netloc for url in CSRF_TRUSTED_ORIGINS]

    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    ALLOWED_HOSTS = ["*"]

CORS_ALLOWED_ORIGINS = [
    "https://cpdtracker-app-712513641417.australia-southeast1.run.app",
]

# Allow cookies/credentials to be sent by the browser (required when frontend uses withCredentials)
CORS_ALLOW_CREDENTIALS = True

# During local development, trust the frontend origin for CSRF when using cookie-based auth/CSRF
# Also includes production frontend URL
CSRF_TRUSTED_ORIGINS = [
    "https://cpdtracker-app-712513641417.australia-southeast1.run.app",
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'social_django',
    'djoser',
    'users',
    'cpd_managements',
    'cpd_activities',
    'cpd_tracking',
    'chats',
    'subscriptions',
    'channels'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

ASGI_APPLICATION = 'config.asgi.application'

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

POSTGRES_DB = os.getenv('POSTGRES_DB', None)
if POSTGRES_DB is None:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB'),
            'USER': os.getenv('POSTGRES_USER'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
            'HOST': os.getenv('POSTGRES_HOST'),
            'PORT': os.getenv('POSTGRES_PORT', None),
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

# Google Cloud Storage settings for static and media files
GS_BUCKET_NAME = os.getenv('GS_BUCKET_NAME', None)

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

GS_DEFAULT_ACL = 'publicRead' # Or 'private' depending on your needs

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'users.authentication.CustomJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}


# Djoser settings
DJOSER = {
    'PASSWORD_RESET_CONFIRM_URL': os.getenv('PASSWORD_RESET_CONFIRM_URL'),
    'SEND_ACTIVATION_EMAIL': True,
    'ACTIVATION_URL': os.getenv('ACTIVATION_URL'),
    'USER_CREATE_PASSWORD_RETYPE': True,
    'PASSWORD_RESET_CONFIRM_RETYPE': True,
    'TOKEN_MODEL': None,
    'SOCIAL_AUTH_ALLOWED_REDIRECT_URIS': os.getenv('REDIRECT_URLS', 'http://localhost:3000').split(','),
    'EMAIL_FRONTEND_DOMAIN': os.getenv('EMAIL_FRONTEND_DOMAIN'),
    'EMAIL_FRONTEND_SITE_NAME': os.getenv('EMAIL_FRONTEND_SITE_NAME'),
}


# Google OAuth2 settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_OAUTH_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_OAUTH_SECRET_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]
SOCIAL_AUTH_GOOGLE_OAUTH2_EXTRA_DATA = [
    ('first_name', 'given_name'),
    ('last_name', 'family_name'),
]

# Microsoft OAuth2 settings
SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = os.getenv('MICROSOFT_OAUTH_KEY')
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = os.getenv('MICROSOFT_OAUTH_SECRET_KEY')
SOCIAL_AUTH_MICROSOFT_GRAPH_SCOPE = [
    'User.Read',
    'openid',
    'profile',
    'email'
]
SOCIAL_AUTH_MICROSOFT_GRAPH_EXTRA_DATA = [
    ('first_name', 'given_name'),
    ('last_name', 'surname'),
]


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.microsoft.MicrosoftOAuth2',
]


# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),

    # cookie settings
    'AUTH_COOKIE': 'access',
    'AUTH_COOKIE_SECURE': True,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'None',
}


# Caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}


# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = 'True'
EMAIL_PORT = '587'


# Stripe Configuration
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

STRIPE_SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:3000/subscriptions/success?session_id={CHECKOUT_SESSION_ID}')
STRIPE_CANCEL_URL = os.getenv('STRIPE_CANCEL_URL', 'http://localhost:3000/subscriptions/cancel?canceled=true')


# Azure OpenAI settings
AZURE_OPENAI_DEPLOYMENT_MODEL = os.getenv('AZURE_OPENAI_DEPLOYMENT_MODEL')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')

AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_MODEL')
