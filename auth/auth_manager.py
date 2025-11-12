# auth/auth_manager.py - VERSÃO ROBUSTA E CONFIÁVEL
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
        self._initialized = False
        self.init_firebase()
    
    def init_firebase(self) -> bool:
        """✅ CORREÇÃO: Inicialização mais robusta com estado claro"""
        try:
            # ✅ CORREÇÃO: Verificar se já está inicializado
            if self._initialized and self.firebase_app:
                logger.info("✅ Firebase Admin já inicializado")
                return True

            if firebase_admin._apps:
                logger.info("✅ Firebase Admin já inicializado (global)")
                self.firebase_app = firebase_admin.get_app()
                self._initialized = True
                return True

            logger.info("🔄 Inicializando Firebase Admin...")
            
            # ✅ ORDEM DE PRIORIDADE CORRETA:
            # 1. Secret File do Render.com (produção)
            # 2. Variável de ambiente (fallback)
            # 3. Arquivo local (desenvolvimento)
            
            secret_file_path = '/etc/secrets/firebase_credentials.json'
            if os.path.exists(secret_file_path):
                try:
                    logger.info("📁 Usando secret file do Render")
                    cred = credentials.Certificate(secret_file_path)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    self._initialized = True
                    logger.info("✅ Firebase Admin inicializado com secret file")
                    return True
                except Exception as e:
                    logger.error(f"❌ Erro com secret file: {e}")
                    # Não retornar aqui, tentar próximo método

            # FALLBACK: Variável de ambiente
            service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
            if service_account_json:
                try:
                    logger.info("📁 Usando variável de ambiente FIREBASE_SERVICE_ACCOUNT")
                    service_account_info = json.loads(service_account_json)
                    cred = credentials.Certificate(service_account_info)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    self._initialized = True
                    logger.info("✅ Firebase Admin inicializado com variável de ambiente")
                    return True
                except Exception as e:
                    logger.error(f"❌ Erro com variável de ambiente: {e}")
                    # Continuar para próximo método

            # FALLBACK: Arquivo local (apenas para desenvolvimento)
            local_file_path = 'firebase_credentials.json'
            if os.path.exists(local_file_path):
                try:
                    logger.info("📁 Usando arquivo local de credenciais")
                    cred = credentials.Certificate(local_file_path)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    self._initialized = True
                    logger.info("✅ Firebase Admin inicializado com arquivo local")
                    return True
                except Exception as e:
                    logger.error(f"❌ Erro com arquivo local: {e}")

            logger.error("❌ Nenhum método de inicialização do Firebase disponível")
            self._initialized = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na inicialização do Firebase: {e}")
            self._initialized = False
            return False

    def is_initialized(self) -> bool:
        """✅ CORREÇÃO: Verificar se está inicializado de forma confiável"""
        return self._initialized and self.firebase_app is not None

    def verify_firebase_token(self, token: str) -> Optional[Dict[str, Any]]:
        """✅ CORREÇÃO: Verificação de token com validações robustas"""
        if not token or len(token) < 100:
            logger.warning("❌ Token inválido ou muito curto")
            return None
            
        try:
            # ✅ CORREÇÃO: Verificar inicialização primeiro
            if not self.is_initialized():
                logger.error("❌ Firebase não inicializado para verificação de token")
                return None

            decoded_token = auth.verify_id_token(token)
            user_email = decoded_token.get('email', 'unknown')
            logger.info(f"✅ Token verificado via Firebase Admin: {user_email}")
            
            return {
                'uid': decoded_token['uid'],
                'email': user_email,
                'name': decoded_token.get('name', user_email.split('@')[0]),
                'picture': decoded_token.get('picture', '/static/images/default-avatar.png'),
                'email_verified': decoded_token.get('email_verified', False),
                'verified_at': datetime.now().isoformat()
            }
            
        except auth.ExpiredIdTokenError:
            logger.warning("❌ Token expirado")
            return None
        except auth.RevokedIdTokenError:
            logger.warning("❌ Token revogado")
            return None
        except auth.InvalidIdTokenError:
            logger.warning("❌ Token inválido")
            return None
        except Exception as e:
            logger.error(f"❌ Erro na verificação do token: {e}")
            return None

    def get_firebase_config_for_frontend(self) -> Dict[str, Any]:
        """✅ CORREÇÃO: Configuração com validação de campos obrigatórios"""
        config = {
            'apiKey': os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY'),
            'authDomain': os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN'),
            'projectId': os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID'),
            'storageBucket': os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET'),
            'messagingSenderId': os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID'),
            'appId': os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID')
        }
        
        # ✅ CORREÇÃO: Validar campos obrigatórios
        required_fields = ['apiKey', 'authDomain', 'projectId']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            logger.error(f"❌ Configuração Firebase incompleta. Campos faltando: {missing_fields}")
            return {}
        
        logger.debug("✅ Configuração Firebase válida para frontend")
        return config

    def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """✅ CORREÇÃO: Obter usuário com validações"""
        if not uid or not isinstance(uid, str):
            logger.warning("❌ UID inválido para busca de usuário")
            return None
            
        try:
            if not self.is_initialized():
                logger.error("❌ Firebase não inicializado para buscar usuário")
                return None
                
            user = auth.get_user(uid)
            logger.info(f"✅ Dados do usuário obtidos: {user.email}")
            
            return {
                'uid': user.uid,
                'email': user.email,
                'name': getattr(user, 'display_name', user.email.split('@')[0]),
                'picture': getattr(user, 'photo_url', '/static/images/default-avatar.png'),
                'email_verified': user.email_verified
            }
        except auth.UserNotFoundError:
            logger.warning(f"❌ Usuário não encontrado: {uid}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao obter usuário {uid}: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """✅ CORREÇÃO: Status detalhado para debug"""
        return {
            'initialized': self.is_initialized(),
            'firebase_app_exists': self.firebase_app is not None,
            'secret_file_exists': os.path.exists('/etc/secrets/firebase_credentials.json'),
            'service_account_available': 'FIREBASE_SERVICE_ACCOUNT' in os.environ,
            'local_file_exists': os.path.exists('firebase_credentials.json'),
            'config_complete': bool(self.get_firebase_config_for_frontend())
        }

# ✅ CORREÇÃO: Instância global com verificação
try:
    auth_manager = AuthManager()
    if auth_manager.is_initialized():
        logger.info("🎉 AuthManager inicializado com sucesso!")
    else:
        logger.error("💥 AuthManager falhou na inicialização")
except Exception as e:
    logger.critical(f"💥 Falha crítica na criação do AuthManager: {e}")
    auth_manager = None