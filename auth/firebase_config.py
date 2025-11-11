import pyrebase
import os

def get_firebase_client():
    """Configuração do cliente Firebase para o frontend"""
    firebase_config = {
        "apiKey": os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY'),
        "authDomain": os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN'),
        "projectId": os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID'),
        "storageBucket": os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET'),
        "messagingSenderId": os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID'),
        "appId": os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID')
    }
    
    firebase = pyrebase.initialize_app(firebase_config)
    return firebase