# auth/auth_manager.py - VERSÃO CORRIGIDA PARA RENDER
import firebase_admin
from firebase_admin import auth, credentials, exceptions
import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.firebase_app = None
        self._initialized = False
        self.init_firebase()
    
    def init_firebase(self) -> bool:
        """Inicialização corrigida para Render"""
        try:
            # Verificar se já existe alguma app inicializada
            if firebase_admin._apps:
                logger.info("✅ Firebase Admin já inicializado (global)")
                self.firebase_app = firebase_admin.get_app()
                self._initialized = True
                return True

            logger.info("🔄 Inicializando Firebase Admin...")
            
            cred = None
            
            # 1. ✅ CORREÇÃO: Secret File do Render (caminho correto)
            secret_file_path = '/etc/secrets/firebase_credentials.json'
            if os.path.exists(secret_file_path):
                try:
                    logger.info("🔑 Usando secret file do Render")
                    cred = credentials.Certificate(secret_file_path)
                    logger.info("✅ Credencial do secret file carregada")
                except Exception as e:
                    logger.error(f"❌ Erro com secret file: {e}")

            # 2. ✅ CORREÇÃO: Variável de ambiente (parse melhorado)
            if not cred:
                service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                if service_account_json:
                    try:
                        logger.info("🔑 Usando variável de ambiente FIREBASE_SERVICE_ACCOUNT")
                        # Limpar e parsear o JSON
                        if service_account_json.startswith('"') and service_account_json.endswith('"'):
                            service_account_json = service_account_json[1:-1].replace('\\n', '\n')
                        
                        service_account_info = json.loads(service_account_json)
                        cred = credentials.Certificate(service_account_info)
                        logger.info("✅ Credencial da variável de ambiente carregada")
                    except Exception as e:
                        logger.error(f"❌ Erro com variável de ambiente: {e}")

            # 3. ✅ CORREÇÃO: Arquivo local (fallback)
            if not cred:
                local_file_path = 'firebase_credentials.json'
                if os.path.exists(local_file_path):
                    try:
                        logger.info("🔑 Usando arquivo local de credenciais")
                        cred = credentials.Certificate(local_file_path)
                        logger.info("✅ Credencial local carregada")
                    except Exception as e:
                        logger.error(f"❌ Erro com arquivo local: {e}")

            if not cred:
                logger.error("❌ Nenhum método de inicialização do Firebase disponível")
                self._initialized = False
                return False

            # ✅ CORREÇÃO: Inicializar sem nome para usar app default
            self.firebase_app = firebase_admin.initialize_app(cred)
            self._initialized = True
            logger.info("✅ Firebase Admin inicializado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na inicialização do Firebase: {e}")
            self._initialized = False
            return False

    def is_initialized(self) -> bool:
        """Verificação robusta de inicialização"""
        try:
            return (self._initialized and 
                   self.firebase_app is not None and 
                   len(firebase_admin._apps) > 0)
        except Exception:
            return False

    def verify_firebase_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificação limpa de token Firebase"""
        if not token or not isinstance(token, str) or len(token) < 100:
            logger.warning("❌ Token inválido ou muito curto")
            return None
            
        try:
            # ✅ CORREÇÃO: Verificar inicialização antes de usar
            if not self.is_initialized():
                logger.error("❌ Firebase não inicializado para verificação de token")
                # Tentar reinicializar
                if not self.init_firebase():
                    logger.error("❌ Falha na reinicialização do Firebase")
                    return None

            # ✅ CORREÇÃO: Verificação direta do token
            decoded_token = auth.verify_id_token(token)
            
            if not decoded_token:
                logger.warning("❌ Token decodificado é None")
                return None

            user_uid = decoded_token.get('uid')
            user_email = decoded_token.get('email', 'unknown')
            
            if not user_uid:
                logger.warning("❌ Token não contém UID")
                return None

            logger.info(f"✅ Token verificado: {user_email}")
            
            user_data = {
                'uid': user_uid,
                'email': user_email,
                'name': decoded_token.get('name') or user_email.split('@')[0],
                'picture': decoded_token.get('picture') or '/static/images/default-avatar.png',
                'email_verified': decoded_token.get('email_verified', False),
                'verified_at': datetime.now().isoformat(),
                'provider': decoded_token.get('firebase', {}).get('sign_in_provider', 'unknown')
            }
            
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
        """Configuração consistente para frontend"""
        config = {
            'apiKey': os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY', 'AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4'),
            'authDomain': os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'popcoin-idle-829ae.firebaseapp.com'),
            'projectId': os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID', 'popcoin-idle-829ae'),
            'storageBucket': os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET', 'popcoin-idle-829ae.firebasestorage.app'),
            'messagingSenderId': os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID', '337350823197'),
            'appId': os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID', '1:337350823197:web:4928ae4827e21c585da5f4')
        }
        
        logger.info("✅ Configuração Firebase carregada para frontend")
        return config

# 🔥 DECORATOR CORRIGIDO
def require_auth(f):
    """
    Decorator para proteger rotas com Firebase token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ✅ CORREÇÃO: Verificar se auth_manager está disponível e inicializado
        if not auth_manager or not auth_manager.is_initialized():
            logger.error("🚫 AuthManager não disponível ou não inicializado")
            return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
        
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("🚫 Requisição sem token de autorização")
            return jsonify({'error': 'Token não fornecido'}), 401
        
        # Extrair token
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        else:
            token = auth_header
        
        if not token:
            logger.warning("🚫 Token malformado")
            return jsonify({'error': 'Token inválido'}), 401
        
        # Verificar token com Firebase
        user_info = auth_manager.verify_firebase_token(token)
        
        if not user_info:
            logger.warning("🚫 Token inválido ou expirado")
            return jsonify({'error': 'Token inválido ou expirado'}), 401
        
        # ✅ INJETAR user_info na request
        request.current_user = user_info
        
        logger.info(f"✅ Requisição autenticada: {user_info['email']}")
        
        return f(*args, **kwargs)
    
    return decorated_function

# ✅ CORREÇÃO: Instância global com inicialização robusta
auth_manager = None

def initialize_auth_manager():
    """Inicialização controlada do AuthManager"""
    global auth_manager
    if auth_manager is None:
        try:
            logger.info("🔄 Criando AuthManager...")
            auth_manager = AuthManager()
            
            if auth_manager.is_initialized():
                logger.info("🎉 AuthManager inicializado com sucesso!")
            else:
                logger.error("💥 AuthManager falhou na inicialização")
                # Tentar inicializar novamente
                if auth_manager.init_firebase():
                    logger.info("🎉 AuthManager inicializado na segunda tentativa!")
                else:
                    logger.error("💥 Falha definitiva na inicialização do AuthManager")
                    
        except Exception as e:
            logger.critical(f"💥 Falha crítica na criação do AuthManager: {e}")
            auth_manager = None
    
    return auth_manager

# ✅ CORREÇÃO: Inicialização imediata e verificada
logger.info("📦 Inicializando auth_manager.py...")
auth_manager = initialize_auth_manager()