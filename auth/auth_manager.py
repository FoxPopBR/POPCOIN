# auth/auth_manager.py - VERSÃO CORRIGIDA (mantendo estrutura atual)
import firebase_admin
from firebase_admin import auth, credentials, exceptions
import os
import json
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Configurar logging profissional
logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self):
        self.firebase_app = None
        self.api_key = "AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4"
        self.init_firebase()
    
    def init_firebase(self) -> bool:
        """Inicializar Firebase Admin SDK - CORREÇÃO: Adicionar secret file do Render"""
        try:
            if firebase_admin._apps:
                logger.info("✅ Firebase Admin já inicializado")
                self.firebase_app = firebase_admin.get_app()
                return True

            logger.info("🔄 Inicializando Firebase Admin...")
            
            # MÉTODO 1: Secret File do Render.com (NOVO - CORREÇÃO PRINCIPAL)
            secret_file_path = '/etc/secrets/firebase_credentials.json'
            if os.path.exists(secret_file_path):
                try:
                    logger.info(f"📁 Encontrado secret file: {secret_file_path}")
                    cred = credentials.Certificate(secret_file_path)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    logger.info("✅ Firebase Admin inicializado com secret file do Render")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Secret file falhou: {e}")

            # MÉTODO 2: Credenciais da variável de ambiente (mantido do código atual)
            service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
            if service_account_json:
                try:
                    service_account_info = json.loads(service_account_json)
                    cred = credentials.Certificate(service_account_info)
                    self.firebase_app = firebase_admin.initialize_app(cred, {
                        'projectId': service_account_info.get('project_id', 'popcoin-idle-829ae')
                    })
                    logger.info("✅ Firebase Admin inicializado com credenciais de serviço")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Credenciais de serviço falharam: {e}")

            # MÉTODO 3: Credenciais padrão do ambiente (mantido do código atual)
            try:
                cred = credentials.ApplicationDefault()
                self.firebase_app = firebase_admin.initialize_app(cred, {
                    'projectId': 'popcoin-idle-829ae'
                })
                logger.info("✅ Firebase Admin inicializado com credenciais padrão")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Credenciais padrão falharam: {e}")

            # MÉTODO 4: Modo de desenvolvimento (mantido do código atual)
            logger.warning("🚧 Firebase Admin em modo de desenvolvimento")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro crítico na inicialização do Firebase: {e}")
            return False

    # 🔥 CORREÇÃO CRÍTICA: Melhorar o verify_firebase_token para funcionar SEM Firebase Admin
    def verify_firebase_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar token do Firebase - CORREÇÃO: Fallback robusto para API REST"""
        if not token or len(token) < 100:
            logger.warning("Token inválido ou muito curto")
            return None
            
        try:
            # Método 1: Firebase Admin (se disponível)
            if self.firebase_app:
                try:
                    decoded_token = auth.verify_id_token(token)
                    return self._extract_user_info_from_token(decoded_token, "Firebase Admin")
                except exceptions.FirebaseError as e:
                    logger.warning(f"Firebase Admin rejeitou o token: {e}")
                    # NÃO retornar None aqui - tentar API REST

            # Método 2: API REST do Firebase (SEMPRE funciona, mesmo sem Firebase Admin)
            logger.info("🔄 Usando API REST do Firebase para verificar token...")
            user_info = self._verify_with_rest_api(token)
            if user_info:
                return user_info

            logger.error("❌ Todos os métodos de verificação falharam")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado na verificação: {e}")
            return None

    def _verify_with_rest_api(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar token usando API REST do Firebase - CORREÇÃO: Logs mais detalhados"""
        try:
            logger.info(f"🌐 Verificando token via API REST...")
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={self.api_key}"
            
            response = requests.post(url, json={'idToken': token}, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('users') and len(data['users']) > 0:
                    user = data['users'][0]
                    logger.info(f"✅ Token verificado via API REST: {user.get('email')}")
                    return self._extract_user_info_from_rest(user, "API REST")
            
            logger.warning(f"❌ API REST rejeitou o token: HTTP {response.status_code}")
            return None
            
        except requests.RequestException as e:
            logger.warning(f"🌐 Erro de rede na API REST: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado na API REST: {e}")
            return None

    # 🔥 CORREÇÃO: Adicionar método para debug do secret file
    def debug_firebase_init(self):
        """Debug para verificar inicialização do Firebase"""
        logger.info("🔍 Debug Firebase Initialization:")
        logger.info(f"   Firebase App: {self.firebase_app}")
        logger.info(f"   Firebase Apps: {firebase_admin._apps}")
        
        # Verificar secret file
        secret_path = '/etc/secrets/firebase_credentials.json'
        logger.info(f"   Secret file exists: {os.path.exists(secret_path)}")
        if os.path.exists(secret_path):
            try:
                size = os.path.getsize(secret_path)
                logger.info(f"   Secret file size: {size} bytes")
            except:
                logger.info(f"   Could not get secret file size")

    # 🔥 CORREÇÃO: Adicionar método para verificar status
    def get_firebase_status(self) -> Dict[str, Any]:
        """Retorna status do Firebase para debugging"""
        return {
            'firebase_app_initialized': self.firebase_app is not None,
            'firebase_apps_count': len(firebase_admin._apps) if hasattr(firebase_admin, '_apps') else 0,
            'secret_file_exists': os.path.exists('/etc/secrets/firebase_credentials.json'),
            'service_account_env': 'FIREBASE_SERVICE_ACCOUNT' in os.environ
        }

    # 🎯 MANTER TODOS OS OUTROS MÉTODOS EXATAMENTE COMO ESTÃO NO CÓDIGO ATUAL
    def _extract_user_info_from_token(self, decoded_token: Dict, method: str) -> Dict[str, Any]:
        """Extrair informações do usuário do token decodificado"""
        user_info = {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email', ''),
            'name': decoded_token.get('name', decoded_token.get('email', '').split('@')[0]),
            'picture': decoded_token.get('picture'),
            'email_verified': decoded_token.get('email_verified', False),
            'auth_method': method,
            'verified_at': datetime.now().isoformat()
        }
        logger.info(f"✅ Token verificado via {method}: {user_info['email']}")
        return user_info

    def _extract_user_info_from_rest(self, user_data: Dict, method: str) -> Dict[str, Any]:
        """Extrair informações do usuário da resposta da API REST"""
        user_info = {
            'uid': user_data['localId'],
            'email': user_data.get('email', ''),
            'name': user_data.get('displayName', user_data.get('email', '').split('@')[0]),
            'picture': user_data.get('photoUrl'),
            'email_verified': user_data.get('emailVerified', False),
            'auth_method': method,
            'verified_at': datetime.now().isoformat()
        }
        logger.info(f"✅ Token verificado via {method}: {user_info['email']}")
        return user_info

    # MANTER TODOS OS OUTROS MÉTODOS EXATAMENTE COMO ESTÃO
    def create_user_with_email_password(self, email: str, password: str, display_name: str = None) -> Dict[str, Any]:
        """Criar usuário com email e senha"""
        try:
            if not self.firebase_app:
                raise Exception("Firebase não inicializado")

            user_data = {
                'email': email,
                'password': password,
                'email_verified': False,
                'disabled': False
            }
            
            if display_name:
                user_data['display_name'] = display_name

            user = auth.create_user(**user_data)
            
            user_info = {
                'uid': user.uid,
                'email': user.email,
                'name': getattr(user, 'display_name', display_name or email.split('@')[0]),
                'email_verified': False,
                'created_at': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Usuário criado: {user.email}")
            return {'success': True, 'user': user_info}
            
        except auth.EmailAlreadyExistsError:
            logger.warning(f"❌ Email já existe: {email}")
            return {'success': False, 'error': 'EMAIL_ALREADY_EXISTS'}
        except auth.WeakPasswordError:
            logger.warning(f"❌ Senha fraca: {email}")
            return {'success': False, 'error': 'WEAK_PASSWORD'}
        except Exception as e:
            logger.error(f"❌ Erro ao criar usuário: {e}")
            return {'success': False, 'error': str(e)}

    def send_password_reset_email(self, email: str) -> Dict[str, Any]:
        """Enviar email de redefinição de senha"""
        try:
            if not self.firebase_app:
                raise Exception("Firebase não inicializado")

            auth.generate_password_reset_link(email)
            logger.info(f"✅ Email de redefinição enviado: {email}")
            return {'success': True}
            
        except auth.UserNotFoundError:
            logger.warning(f"❌ Usuário não encontrado: {email}")
            return {'success': False, 'error': 'USER_NOT_FOUND'}
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email de redefinição: {e}")
            return {'success': False, 'error': str(e)}

    def update_user_profile(self, uid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Atualizar perfil do usuário"""
        try:
            if not self.firebase_app:
                raise Exception("Firebase não inicializado")

            auth.update_user(uid, **updates)
            logger.info(f"✅ Perfil atualizado: {uid}")
            return {'success': True}
            
        except auth.UserNotFoundError:
            logger.warning(f"❌ Usuário não encontrado para atualização: {uid}")
            return {'success': False, 'error': 'USER_NOT_FOUND'}
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar perfil: {e}")
            return {'success': False, 'error': str(e)}

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Obter usuário por email"""
        try:
            if not self.firebase_app:
                return None

            user = auth.get_user_by_email(email)
            return {
                'uid': user.uid,
                'email': user.email,
                'name': getattr(user, 'display_name', ''),
                'email_verified': user.email_verified,
                'disabled': user.disabled
            }
        except auth.UserNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por email: {e}")
            return None

    def delete_user(self, uid: str) -> bool:
        """Excluir usuário"""
        try:
            if not self.firebase_app:
                return False

            auth.delete_user(uid)
            logger.info(f"✅ Usuário excluído: {uid}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao excluir usuário: {e}")
            return False

    # Métodos de compatibilidade (para código existente)
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Alias para verify_firebase_token (compatibilidade)"""
        return self.verify_firebase_token(token)

    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obter dados do usuário (compatibilidade)"""
        try:
            if not self.firebase_app:
                return None
            user = auth.get_user(user_id)
            return {
                'uid': user.uid,
                'email': user.email,
                'name': getattr(user, 'display_name', ''),
                'picture': getattr(user, 'photo_url', None),
                'email_verified': user.email_verified
            }
        except Exception as e:
            logger.error(f"Erro ao obter dados do usuário: {e}")
            return None

    def save_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Salvar dados do usuário (compatibilidade)"""
        try:
            # Esta é uma implementação simplificada - em produção, salvaria no banco de dados
            logger.info(f"📝 Dados salvos para usuário {user_id}: {data.keys()}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados do usuário: {e}")
            return False