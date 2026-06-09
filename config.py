import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hospital_management_secret_key_2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hospital.db')
    if SQLALCHEMY_DATABASE_URI:
        # Remove channel_binding param which causes SSL issues with Neon
        if 'channel_binding=' in SQLALCHEMY_DATABASE_URI:
            parts = SQLALCHEMY_DATABASE_URI.split('&')
            parts = [p for p in parts if not p.startswith('channel_binding=')]
            SQLALCHEMY_DATABASE_URI = '&'.join(parts)
        if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql+psycopg://', 1)
        elif SQLALCHEMY_DATABASE_URI.startswith('postgresql://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgresql://', 'postgresql+psycopg://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'connect_timeout': 10}
    }
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_hospital.db'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
