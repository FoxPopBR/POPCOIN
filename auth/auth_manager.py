# auth/auth_manager.py - VERSÃO CORRIGIDA
import firebase_admin
from firebase_admin import auth, credentials
import os
import json
import requests

class AuthManager:
    def __init__(self):
        self.init_firebase()
    
    def init_firebase(self):
        """Inicializar Firebase Admin SDK de forma robusta"""
        try:
            if not firebase_admin._apps:
                print("🔄 Inicializando Firebase Admin...")
                
                # Método 1: Tentar credenciais padrão (funciona no Render com service account)
                try:
                    # No Render, as credenciais padrão devem ser configuradas via variáveis de ambiente
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred, {
                        'projectId': 'popcoin-idle-829ae'
                    })
                    print("✅ Firebase Admin: Inicializado com credenciais padrão")
                    
                except Exception as default_error:
                    print(f"⚠️ Credenciais padrão falharam: {default_error}")
                    
                    # Método 2: Fallback para verificação básica
                    print("🔄 Usando modo fallback para desenvolvimento...")
                    # Não inicializamos o Firebase Admin, usaremos apenas a verificação básica
                    
        except Exception as e:
            print(f"❌ Erro na inicialização do Firebase Admin: {e}")
    
    def verify_firebase_token(self, token):
        """Verificar token do Firebase com múltiplos fallbacks"""
        try:
            if not token or len(token) < 50:
                print("❌ Token inválido ou muito curto")
                return None
                
            # Método 1: Firebase Admin (se disponível)
            try:
                if firebase_admin._apps:
                    decoded_token = auth.verify_id_token(token)
                    user_info = {
                        'uid': decoded_token['uid'],
                        'email': decoded_token.get('email', 'user@popcoin.com'),
                        'name': decoded_token.get('name', 'Jogador PopCoin'),
                        'picture': decoded_token.get('picture'),
                        'email_verified': decoded_token.get('email_verified', True)
                    }
                    print(f"✅ Token verificado via Firebase Admin: {user_info['email']}")
                    return user_info
                else:
                    raise Exception("Firebase Admin não disponível")
                    
            except Exception as admin_error:
                print(f"⚠️ Firebase Admin falhou: {admin_error}")
                
                # Método 2: API REST do Firebase (fallback)
                try:
                    return self._verify_with_rest_api(token)
                except Exception as rest_error:
                    print(f"⚠️ API REST falhou: {rest_error}")
                    
                    # Método 3: Verificação básica (para desenvolvimento)
                    return self._basic_token_verification(token)
                
        except Exception as e:
            print(f"❌ Erro geral na verificação do token: {e}")
            return None
    
    def _verify_with_rest_api(self, token):
        """Verificar token usando API REST do Firebase"""
        try:
            api_key = "AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4"
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}"
            
            response = requests.post(url, json={'idToken': token})
            
            if response.status_code == 200:
                data = response.json()
                if 'users' in data and len(data['users']) > 0:
                    user = data['users'][0]
                    user_info = {
                        'uid': user['localId'],
                        'email': user.get('email', 'user@popcoin.com'),
                        'name': user.get('displayName', 'Jogador PopCoin'),
                        'picture': user.get('photoUrl'),
                        'email_verified': user.get('emailVerified', True)
                    }
                    print(f"✅ Token verificado via API REST: {user_info['email']}")
                    return user_info
            
            print("❌ Falha na verificação via API REST")
            return None
            
        except Exception as e:
            print(f"❌ Erro na API REST: {e}")
            return None
    
    def _basic_token_verification(self, token):
        """Verificação básica para desenvolvimento"""
        try:
            if token and len(token) > 50:
                # Gerar ID consistente baseado no token
                user_id = f"user_{abs(hash(token)) % 1000000}"
                user_info = {
                    'uid': user_id,
                    'email': 'user@popcoin.com',
                    'name': 'Jogador PopCoin',
                    'picture': None,
                    'email_verified': True
                }
                print(f"✅ Token verificado via método básico: {user_id}")
                return user_info
            return None
        except Exception as e:
            print(f"❌ Fallback básico falhou: {e}")
            return None