"""
Django settings for somatic_variant_db project.

Generated by 'django-admin startproject' using Django 3.1.8.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'm#4qhi$dr8)i$ed1)yfuc68ebtuwfo+5mlyy7rtbf7%l-a%kq)'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', '10.59.210.247', '.pythonanywhere.com']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'analysis',
    'svig',
    'crispy_forms',
    'auditlog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
]

ROOT_URLCONF = 'somatic_variant_db.urls'

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

WSGI_APPLICATION = 'somatic_variant_db.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases


DB_INSTANCE = 'cluster'
if DB_INSTANCE == 'local':

	DATABASES = {
		'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
 		}
	}

else:
    DB_PASSWORD_FILE = 'password.txt'
    with open(DB_PASSWORD_FILE) as f:
        db_password = f.readline().strip()

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'somatic_variant_db',
            'USER': 'somatic_variant_db_user',
            'PASSWORD': db_password,
            'HOST': 'localhost',
            'PORT': '',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-GB'

TIME_ZONE = 'Europe/London'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "somatic_variant_db","static"),
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = '/login/'

## SVIG settings

SVIG_CODE_VERSION = 'v1.0'

BIOLOGICAL_CLASS_CHOICES = (
    ('B', 'Benign'),
    ('LB', 'Likely benign'),
    ('V', 'VUS'),
    ('LO', 'Likely oncogenic'),
    ('O', 'Oncogenic'),
)

CLINICAL_CLASS_CHOICES = (
    ('1A', 'Tier IA'),
    ('1B', 'Tier IB'),
    ('2C', 'Tier IIC'),
    ('2D', 'Tier IID'),
    ('3', 'Tier III'),
    ('4', 'Tier IV'),
)

CODE_PRETTY_PRINT = {
    'SA': 'Stand-alone',
    'VS': 'Very strong',
    'ST': 'Strong',
    'MO': 'Moderate',
    'SU': 'Supporting',
    'PE': 'Pending',
    'NA': 'Not applied',
}

CODE_SCORES = {'SA': 100, 'VS': 8, 'ST': 4, 'MO': 2, 'SU': 1}
