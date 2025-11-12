# auth/auth_manager.py - VERSÃO SIMPLIFICADA E CORRETA
import firebase_admin
from firebase_admin import auth, credentials
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.firebase_app = None
        self.init_firebase()
    
    def init_firebase(self) -> bool:
        """Inicializar Firebase Admin SDK de forma SIMPLES e CONFIÁVEL"""
        try:
            if firebase_admin._apps:
                logger.info("✅ Firebase Admin já inicializado")
                self.firebase_app = firebase_admin.get_app()
                return True

            logger.info("🔄 Inicializando Firebase Admin...")
            
            # MÉTODO ÚNICO E CONFIÁVEL: Secret File do Render.com
            secret_file_path = '/etc/secrets/firebase_credentials.json'
            if os.path.exists(secret_file_path):
                try:
                    logger.info("📁 Usando secret file do Render")
                    cred = credentials.Certificate(secret_file_path)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    logger.info("✅ Firebase Admin inicializado com secret file")
                    return True
                except Exception as e:
                    logger.error(f"❌ Erro com secret file: {e}")
                    return False

            # FALLBACK: Variável de ambiente (apenas se secret file não existir)
            service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
            if service_account_json:
                try:
                    logger.info("📁 Usando variável de ambiente FIREBASE_SERVICE_ACCOUNT")
                    service_account_info = json.loads(service_account_json)
                    cred = credentials.Certificate(service_account_info)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    logger.info("✅ Firebase Admin inicializado com variável de ambiente")
                    return True
                except Exception as e:
                    logger.error(f"❌ Erro com variável de ambiente: {e}")
                    return False

            logger.error("❌ Nenhum método de inicialização do Firebase disponível")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na inicialização do Firebase: {e}")
            return False

    def verify_firebase_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar token do Firebase de forma SIMPLES - APENAS Firebase Admin"""
        if not token or len(token) < 100:
            logger.warning("❌ Token inválido ou muito curto")
            return None
            
        try:
            # MÉTODO ÚNICO: Firebase Admin (o mais confiável)
            if not self.firebase_app:
                logger.error("❌ Firebase não inicializado")
                return None

            decoded_token = auth.verify_id_token(token)
            logger.info(f"✅ Token verificado via Firebase Admin: {decoded_token.get('email')}")
            
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email', ''),
                'name': decoded_token.get('name', decoded_token.get('email', '').split('@')[0]),
                'picture': decoded_token.get('picture', '/static/images/default-avatar.png'),
                'email_verified': decoded_token.get('email_verified', False),
                'verified_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Token inválido: {e}")
            return None

    def get_firebase_config_for_frontend(self) -> Dict[str, Any]:
        """Fornecer configuração pública do Firebase para o frontend"""
        return {
            'apiKey': os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY'),
            'authDomain': os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN'),
            'projectId': os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID'),
            'storageBucket': os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET'),
            'messagingSenderId': os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID'),
            'appId': os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID')
        }

    # 🎯 MÉTODOS ESSENCIAIS APENAS - remover complexidade desnecessária
    def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """Obter dados do usuário pelo UID"""
        try:
            if not self.firebase_app:
                return None
                
            user = auth.get_user(uid)
            return {
                'uid': user.uid,
                'email': user.email,
                'name': getattr(user, 'display_name', user.email.split('@')[0]),
                'picture': getattr(user, 'photo_url', '/static/images/default-avatar.png'),
                'email_verified': user.email_verified
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter usuário {uid}: {e}")
            return None

    # 🔥 MÉTODO DE DEBUG SIMPLIFICADO
    def get_status(self) -> Dict[str, Any]:
        """Status simplificado para debug"""
        return {
            'firebase_initialized': self.firebase_app is not None,
            'secret_file_exists': os.path.exists('/etc/secrets/firebase_credentials.json'),
            'service_account_available': 'FIREBASE_SERVICE_ACCOUNT' in os.environ
        }

# Instância global para uso em toda a aplicação
auth_manager = AuthManager()