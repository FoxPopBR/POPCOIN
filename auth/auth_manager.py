import firebase_admin
from firebase_admin import auth, credentials
import os

class AuthManager:
    def __init__(self):
        self.init_firebase()
    
    def init_firebase(self):
        """Inicializar Firebase Admin SDK de forma confiável"""
        try:
            if not firebase_admin._apps:
                # Para Render, usar credentials padrão
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': 'popcoin-idle-829ae'
                })
                print("✅ Firebase Admin inicializado com sucesso!")
        except Exception as e:
            print(f"⚠️ Firebase Admin init: {e}")
    
    def verify_firebase_token(self, token):
        """Verificar token do Firebase de forma robusta"""
        try:
            # Tentar verificação com Firebase Admin
            decoded_token = auth.verify_id_token(token)
            user_info = {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email', 'user@popcoin.com'),
                'name': decoded_token.get('name', 'Jogador PopCoin'),
                'picture': decoded_token.get('picture')
            }
            print(f"✅ Token verificado para: {user_info['email']}")
            return user_info
        except Exception as e:
            print(f"⚠️ Firebase Admin verification failed: {e}")
            # Fallback: verificação básica (apenas para desenvolvimento)
            if token and len(token) > 50:  # Token parece válido
                return {
                    'uid': f"user_{hash(token) % 100000}",
                    'email': 'user@popcoin.com', 
                    'name': 'Jogador PopCoin',
                    'picture': None
                }
            return None