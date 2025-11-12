# auth/auth_manager.py - VERSÃO CORRIGIDA E OTIMIZADA
import firebase_admin
from firebase_admin import auth, credentials, exceptions
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
        """✅ CORREÇÃO: Inicialização simplificada e confiável"""
        try:
            # ✅ CORREÇÃO: Verificar se já está inicializado
            if self._initialized and self.firebase_app:
                logger.info("✅ Firebase Admin já inicializado")
                return True

            # ✅ CORREÇÃO: Verificar apps existentes
            if firebase_admin._apps:
                logger.info("✅ Firebase Admin já inicializado (global)")
                self.firebase_app = firebase_admin.get_app()
                self._initialized = True
                return True

            logger.info("🔄 Inicializando Firebase Admin...")
            
            # ✅ CORREÇÃO: Ordem de prioridade otimizada
            cred = None
            
            # 1. Secret File do Render.com (produção)
            secret_file_path = '/etc/secrets/firebase_credentials.json'
            if os.path.exists(secret_file_path):
                try:
                    logger.info("📁 Usando secret file do Render")
                    cred = credentials.Certificate(secret_file_path)
                except Exception as e:
                    logger.error(f"❌ Erro com secret file: {e}")

            # 2. Variável de ambiente (fallback)
            if not cred:
                service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                if service_account_json:
                    try:
                        logger.info("📁 Usando variável de ambiente FIREBASE_SERVICE_ACCOUNT")
                        service_account_info = json.loads(service_account_json)
                        cred = credentials.Certificate(service_account_info)
                    except Exception as e:
                        logger.error(f"❌ Erro com variável de ambiente: {e}")

            # 3. Arquivo local (desenvolvimento)
            if not cred:
                local_file_path = 'firebase_credentials.json'
                if os.path.exists(local_file_path):
                    try:
                        logger.info("📁 Usando arquivo local de credenciais")
                        cred = credentials.Certificate(local_file_path)
                    except Exception as e:
                        logger.error(f"❌ Erro com arquivo local: {e}")

            if not cred:
                logger.error("❌ Nenhum método de inicialização do Firebase disponível")
                self._initialized = False
                return False

            # ✅ CORREÇÃO: Inicializar com nome específico para evitar conflitos
            self.firebase_app = firebase_admin.initialize_app(cred, name='popcoin-app')
            self._initialized = True
            logger.info("✅ Firebase Admin inicializado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na inicialização do Firebase: {e}")
            self._initialized = False
            return False

    def is_initialized(self) -> bool:
        """✅ CORREÇÃO: Verificação robusta de inicialização"""
        try:
            return (self._initialized and 
                   self.firebase_app is not None and 
                   len(firebase_admin._apps) > 0)
        except Exception:
            return False

    def verify_firebase_token(self, token: str) -> Optional[Dict[str, Any]]:
        """✅ CORREÇÃO: Verificação de token otimizada"""
        if not token or not isinstance(token, str) or len(token) < 100:
            logger.warning("❌ Token inválido ou muito curto")
            return None
            
        try:
            # ✅ CORREÇÃO: Verificação mais robusta
            if not self.is_initialized():
                logger.error("❌ Firebase não inicializado para verificação de token")
                if not self.init_firebase():
                    return None

            decoded_token = auth.verify_id_token(token)
            if not decoded_token:
                logger.warning("❌ Token decodificado é None")
                return None

            user_email = decoded_token.get('email', 'unknown')
            user_uid = decoded_token.get('uid')
            
            if not user_uid:
                logger.warning("❌ Token não contém UID")
                return None

            logger.info(f"✅ Token verificado: {user_email}")
            
            # ✅ CORREÇÃO: Dados completos do usuário
            user_data = {
                'uid': user_uid,
                'email': user_email,
                'name': decoded_token.get('name') or user_email.split('@')[0],
                'picture': decoded_token.get('picture') or '/static/images/default-avatar.png',
                'email_verified': decoded_token.get('email_verified', False),
                'verified_at': datetime.now().isoformat(),
                'provider': decoded_token.get('firebase', {}).get('sign_in_provider', 'unknown')
            }
            
            # ✅ CORREÇÃO: Obter dados adicionais se disponível
            try:
                user_record = auth.get_user(user_uid)
                if user_record:
                    user_data.update({
                        'name': user_record.display_name or user_data['name'],
                        'picture': user_record.photo_url or user_data['picture'],
                        'email_verified': user_record.email_verified
                    })
            except Exception as user_error:
                logger.debug(f"ℹ️ Não foi possível obter dados adicionais do usuário: {user_error}")
            
            return user_data
            
        except auth.ExpiredIdTokenError:
            logger.warning("❌ Token expirado")
            return None
        except auth.RevokedIdTokenError:
            logger.warning("❌ Token revogado")
            return None
        except auth.InvalidIdTokenError:
            logger.warning("❌ Token inválido")
            return None
        except exceptions.FirebaseError as firebase_error:
            logger.error(f"❌ Erro do Firebase na verificação: {firebase_error}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado na verificação do token: {e}")
            return None

    def get_firebase_config_for_frontend(self) -> Dict[str, Any]:
        """✅ CORREÇÃO: Configuração consistente para frontend"""
        config = {
            'apiKey': os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY', 'AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4'),
            'authDomain': os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'popcoin-idle-829ae.firebaseapp.com'),
            'projectId': os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID', 'popcoin-idle-829ae'),
            'storageBucket': os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET', 'popcoin-idle-829ae.firebasestorage.app'),
            'messagingSenderId': os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID', '337350823197'),
            'appId': os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID', '1:337350823197:web:4928ae4827e21c585da5f4')
        }
        
        # ✅ CORREÇÃO: Validar campos obrigatórios
        required_fields = ['apiKey', 'authDomain', 'projectId']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            logger.error(f"❌ Configuração Firebase incompleta. Campos faltando: {missing_fields}")
            # ✅ CORREÇÃO: Não retornar vazio, usar valores padrão
            return {
                'apiKey': 'AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4',
                'authDomain': 'popcoin-idle-829ae.firebaseapp.com',
                'projectId': 'popcoin-idle-829ae',
                'storageBucket': 'popcoin-idle-829ae.firebasestorage.app',
                'messagingSenderId': '337350823197',
                'appId': '1:337350823197:web:4928ae4827e21c585da5f4'
            }
        
        logger.info("✅ Configuração Firebase válida para frontend")
        return config

    def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """✅ CORREÇÃO: Obter usuário com tratamento de erro melhorado"""
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
                'name': user.display_name or user.email.split('@')[0],
                'picture': user.photo_url or '/static/images/default-avatar.png',
                'email_verified': user.email_verified,
                'created_at': user.user_metadata.creation_timestamp.isoformat() if user.user_metadata.creation_timestamp else datetime.now().isoformat()
            }
        except auth.UserNotFoundError:
            logger.warning(f"❌ Usuário não encontrado: {uid}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao obter usuário {uid}: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """✅ CORREÇÃO: Status detalhado para debug"""
        try:
            config = self.get_firebase_config_for_frontend()
            return {
                'initialized': self.is_initialized(),
                'firebase_app_exists': self.firebase_app is not None,
                'apps_count': len(firebase_admin._apps) if firebase_admin._apps else 0,
                'secret_file_exists': os.path.exists('/etc/secrets/firebase_credentials.json'),
                'service_account_available': 'FIREBASE_SERVICE_ACCOUNT' in os.environ,
                'local_file_exists': os.path.exists('firebase_credentials.json'),
                'config_complete': bool(config and config.get('apiKey')),
                'config_keys': list(config.keys()) if config else []
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter status: {e}")
            return {'error': str(e)}

    def health_check(self) -> Dict[str, Any]:
        """✅ NOVO: Health check específico para o Firebase"""
        try:
            status = self.get_status()
            
            if not status['initialized']:
                return {
                    'healthy': False,
                    'message': 'Firebase não inicializado',
                    'status': status
                }
            
            # Testar funcionalidade básica
            test_uid = 'test-health-check'
            try:
                # Tentar uma operação simples
                auth.get_user('nonexistent-user-test-123')
            except auth.UserNotFoundError:
                # Isso é esperado - significa que o Firebase está funcionando
                pass
            except Exception as e:
                logger.warning(f"⚠️ Health check detectou problema: {e}")
                return {
                    'healthy': False,
                    'message': f'Firebase com problemas: {e}',
                    'status': status
                }
            
            return {
                'healthy': True,
                'message': 'Firebase operacional',
                'status': status
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no health check: {e}")
            return {
                'healthy': False,
                'message': f'Erro no health check: {e}',
                'status': {'error': str(e)}
            }

# ✅ CORREÇÃO: Instância global com inicialização controlada
auth_manager = None

def get_auth_manager():
    """Singleton para AuthManager com inicialização controlada"""
    global auth_manager
    if auth_manager is None:
        try:
            logger.info("🔄 Criando AuthManager...")
            auth_manager = AuthManager()
            
            if auth_manager.is_initialized():
                logger.info("🎉 AuthManager inicializado com sucesso!")
                
                # Log do status para debug
                status = auth_manager.get_status()
                logger.info(f"📊 Status do AuthManager: {status}")
            else:
                logger.error("💥 AuthManager falhou na inicialização")
                
        except Exception as e:
            logger.critical(f"💥 Falha crítica na criação do AuthManager: {e}")
            auth_manager = None
    
    return auth_manager

# Inicialização controlada
logger.info("📦 Inicializando auth_manager.py...")
auth_manager = get_auth_manager()