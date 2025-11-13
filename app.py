# app.py - VERSÃO CORRIGIDA
from functools import wraps
import os
import json
import time
import logging
import secrets
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ✅ CONFIGURAÇÃO MÍNIMA - Sem sessões complexas
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ✅ CORREÇÃO: Importar e inicializar managers em ordem
try:
    from auth.auth_manager import auth_manager, require_auth, initialize_auth_manager
    # Forçar inicialização do auth_manager
    auth_manager = initialize_auth_manager()
    if auth_manager and auth_manager.is_initialized():
        logger.info("✅ AuthManager e require_auth carregados")
    else:
        logger.error("❌ AuthManager não inicializado corretamente")
        # Criar um require_auth fallback
        def require_auth_fallback(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
            return decorated_function
        require_auth = require_auth_fallback
except Exception as e:
    logger.error(f"❌ Erro crítico no AuthManager: {e}")
    auth_manager = None
    # Fallback para require_auth
    def require_auth(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return jsonify({'error': 'Sistema de autenticação indisponível'}), 503
        return decorated_function

try:
    from game.game_logic import GameManager
    game_manager = GameManager()
    logger.info("✅ GameManager carregado")
except Exception as e:
    logger.warning(f"⚠️ GameManager não disponível: {e}")
    game_manager = None

try:
    from database.db_models import DatabaseManager
    db_manager = DatabaseManager()
    logger.info("✅ DatabaseManager carregado")
except Exception as e:
    logger.warning(f"⚠️ DatabaseManager não disponível: {e}")
    db_manager = None

# ✅ CACHE para configuração Firebase
firebase_config_cache = None
firebase_config_loaded = False

def get_firebase_config():
    """Obter configuração Firebase (com cache e fallback)"""
    global firebase_config_cache, firebase_config_loaded
    
    if firebase_config_loaded:
        return firebase_config_cache or {}
        
    try:
        if auth_manager and auth_manager.is_initialized():
            firebase_config_cache = auth_manager.get_firebase_config_for_frontend()
            logger.info("✅ Configuração Firebase carregada do AuthManager")
        else:
            # Fallback direto das variáveis de ambiente
            firebase_config_cache = {
                'apiKey': os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY', 'AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4'),
                'authDomain': os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'popcoin-idle-829ae.firebaseapp.com'),
                'projectId': os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID', 'popcoin-idle-829ae'),
                'storageBucket': os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET', 'popcoin-idle-829ae.firebasestorage.app'),
                'messagingSenderId': os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID', '337350823197'),
                'appId': os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID', '1:337350823197:web:4928ae4827e21c585da5f4')
            }
            logger.info("✅ Configuração Firebase carregada do ambiente")
        
        firebase_config_loaded = True
        return firebase_config_cache
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração Firebase: {e}")
        return {}

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página inicial - PÚBLICA (apenas login)"""
    logger.info("🏠 Página inicial (login)")
    firebase_config = get_firebase_config()
    return render_template('index.html', firebase_config=firebase_config)

@app.route('/game')
def game():
    """Página do jogo - PROTEGIDA (frontend valida)"""
    logger.info("🎮 Página do jogo (protegida)")
    firebase_config = get_firebase_config()
    return render_template('game.html', firebase_config=firebase_config)

@app.route('/profile')
def profile():
    """Página de perfil - PROTEGIDA (frontend valida)"""
    logger.info("👤 Página de perfil (protegida)")
    firebase_config = get_firebase_config()
    return render_template('profile.html', firebase_config=firebase_config)

# ========== API DE AUTENTICAÇÃO ==========

@app.route('/api/auth/verify', methods=['POST'])
def auth_verify():
    """🔥 VERIFICAÇÃO PURA DO FIREBASE"""
    try:
        data = request.get_json()
        token = data.get('token') if data else None

        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400

        logger.info("🔍 Verificando token Firebase...")
        
        # ✅ CORREÇÃO: Verificação direta com fallback
        if auth_manager and auth_manager.is_initialized():
            user_info = auth_manager.verify_firebase_token(token)
        else:
            logger.error("❌ AuthManager não disponível para verificação")
            return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
        
        if not user_info:
            logger.warning("❌ Token inválido")
            return jsonify({'error': 'Token inválido ou expirado'}), 401

        logger.info(f"✅ Token verificado: {user_info['email']}")
        
        return jsonify({
            'success': True,
            'user': user_info
        })
            
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/auth/firebase-config')
def firebase_config_api():
    """Fornecer configuração do Firebase para o frontend"""
    try:
        config = get_firebase_config()
        return jsonify(config)
    except Exception as e:
        logger.error(f"❌ Erro ao fornecer configuração Firebase: {e}")
        return jsonify({'error': 'Erro de configuração'}), 500

# ========== API DE USUÁRIO (PROTEGIDAS) ==========

@app.route('/api/user/profile', methods=['GET'])
@require_auth
def user_profile():
    """PROTEGIDA - Obter perfil do usuário"""
    try:
        user_info = request.current_user  # Injetado pelo decorator
        user_id = user_info['uid']

        # Carregar dados completos do banco
        user_data = user_info.copy()
        if db_manager:
            try:
                stored_data = db_manager.get_user_data(user_id)
                if stored_data:
                    user_data.update(stored_data)
                    logger.info(f"✅ Dados do banco carregados para: {user_id}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao carregar perfil do banco: {db_error}")
        
        return jsonify({
            'success': True, 
            'profile': user_data
        })
            
    except Exception as e:
        logger.error(f"❌ Erro no perfil: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/create', methods=['POST'])
@require_auth
def user_create():
    """PROTEGIDA - Criar usuário no banco"""
    try:
        user_info = request.current_user
        user_id = user_info['uid']

        if db_manager:
            user_data = {
                'uid': user_id,
                'email': user_info['email'],
                'name': user_info['name'],
                'picture': user_info['picture'],
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat()
            }
            
            success = db_manager.create_user(user_id, user_data)
            if success:
                logger.info(f"✅ Usuário criado no banco: {user_id}")
                return jsonify({'success': True, 'message': 'Usuário criado com sucesso'})
            else:
                return jsonify({'error': 'Erro ao criar usuário'}), 500
        else:
            return jsonify({'error': 'Banco de dados não disponível'}), 503
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar usuário: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

# ========== API DO JOGO (PROTEGIDAS) ==========

@app.route('/api/game/state', methods=['GET'])
@require_auth
def get_game_state():
    """PROTEGIDA - Obter estado do jogo"""
    try:
        user_info = request.current_user
        user_id = user_info['uid']

        game_data = {}
        
        # Tentar carregar do game_manager
        if game_manager:
            try:
                game_data = game_manager.get_user_game_state(user_id)
            except Exception as mgr_error:
                logger.warning(f"⚠️ Erro no game_manager: {mgr_error}")
        
        # Fallback para db_manager
        if not game_data and db_manager:
            try:
                stored_data = db_manager.get_user_data(user_id)
                if stored_data:
                    game_data = stored_data.get('game_data', {})
            except Exception as db_error:
                logger.warning(f"⚠️ Erro no banco: {db_error}")
        
        # Dados padrão se não encontrar nada
        if not game_data:
            game_data = {
                'coins': 0,
                'coins_per_click': 1,
                'coins_per_second': 0,
                'total_coins': 0,
                'prestige_level': 0,
                'upgrades': {
                    'click_power': 1,
                    'auto_clickers': 0,
                    'click_bots': 0
                },
                'click_count': 0,
                'last_update': time.time(),
                'inventory': [],
                'achievements': []
            }
        
        return jsonify(game_data)
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter estado do jogo: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/game/save', methods=['POST'])
@require_auth
def save_game_state():
    """PROTEGIDA - Salvar estado do jogo"""
    try:
        user_info = request.current_user
        user_id = user_info['uid']
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        # Salvar no game_manager
        save_success = True
        if game_manager:
            try:
                save_success = game_manager.save_game_state(user_id, data)
            except Exception as mgr_error:
                logger.warning(f"⚠️ Erro ao salvar no game_manager: {mgr_error}")
                save_success = False
        
        # Salvar no db_manager também
        if db_manager:
            try:
                user_data = db_manager.get_user_data(user_id) or {}
                user_data['game_data'] = data
                user_data['last_activity'] = datetime.now().isoformat()
                
                db_manager.save_user_data(user_id, user_data)
                logger.info(f"✅ Estado do jogo salvo no banco: {user_id}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar no banco: {db_error}")
        
        return jsonify({'success': save_success})
            
    except Exception as e:
        logger.error(f"❌ Erro ao salvar estado do jogo: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

# ========== ROTAS DO SISTEMA ==========

@app.route('/healthz')
def health_check():
    """Health check para Render"""
    return 'OK'

@app.route('/api/system/health')
def system_health():
    """Health check completo do sistema"""
    auth_status = 'available' if (auth_manager and auth_manager.is_initialized()) else 'unavailable'
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'authentication': auth_status,
            'game_system': 'available' if game_manager else 'unavailable',
            'database': 'available' if db_manager else 'unavailable'
        }
    })

# ========== MANIPULADOR DE ERROS ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Erro interno: {error}")
    return jsonify({'error': 'Erro interno do servidor'}), 500

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Não autorizado'}), 401

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"🚀 Iniciando PopCoin IDLE na porta {port}")
    logger.info(f"🔥 Sistema de autenticação: Firebase Auth Puro (Stateless)")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)