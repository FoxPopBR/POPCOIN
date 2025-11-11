import firebase_admin
from firebase_admin import auth, credentials
import os

class AuthManager:
    def __init__(self):
        self.init_firebase()
    
    def init_firebase(self):
        """Inicializar Firebase Admin SDK"""
        try:
            # Para produção, usar variáveis de ambiente
            if not firebase_admin._apps:
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID'),
                    "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
                    "private_key": os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
                    "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
                    "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_CERT_URL')
                })
                firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Firebase Admin init error: {e}")
    
    def verify_firebase_token(self, token):
        """Verificar token do Firebase"""
        try:
            decoded_token = auth.verify_id_token(token)
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture')
            }
        except Exception as e:
            print(f"Token verification error: {e}")
            return None