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

# Importar managers
try:
    from auth.auth_manager import auth_manager, require_auth
    logger.info("✅ AuthManager e require_auth carregados")
except Exception as e:
    logger.warning(f"⚠️ AuthManager não disponível: {e}")
    auth_manager = None
    require_auth = None

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

def get_firebase_config():
    """Obter configuração Firebase (com cache)"""
    global firebase_config_cache
    if firebase_config_cache is None and auth_manager:
        try:
            firebase_config_cache = auth_manager.get_firebase_config_for_frontend()
            logger.info("✅ Configuração Firebase carregada e cacheada")
        except Exception as e:
            logger.error(f"❌ Erro ao obter configuração Firebase: {e}")
            firebase_config_cache = {}
    return firebase_config_cache or {}

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
    """🔥 VERIFICAÇÃO PURA DO FIREBASE - Sem sessões Flask"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400

        logger.info("🔍 Verificando token Firebase...")
        user_info = auth_manager.verify_firebase_token(token)
        
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

@app.route('/api/user/profile', methods=['GET', 'PUT'])
@require_auth
def user_profile():
    """PROTEGIDA - Obter ou atualizar perfil"""
    user_info = request.current_user  # Injetado pelo decorator
    user_id = user_info['uid']

    try:
        if request.method == 'GET':
            # Carregar dados completos do banco
            if db_manager:
                try:
                    stored_data = db_manager.get_user_data(user_id)
                    if stored_data:
                        user_info.update(stored_data)
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao carregar perfil do banco: {db_error}")
            
            return jsonify({
                'success': True, 
                'profile': user_info
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Campos permitidos para atualização
            allowed_fields = ['name', 'preferences']
            
            updated_data = user_info.copy()
            for field in allowed_fields:
                if field in data:
                    updated_data[field] = data[field]
            
            updated_data['last_activity'] = datetime.now().isoformat()
            
            # Salvar no banco
            if db_manager:
                try:
                    db_manager.save_user_data(user_id, updated_data)
                    logger.info(f"✅ Perfil salvo no banco: {user_id}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar perfil: {db_error}")
            
            logger.info(f"✅ Perfil atualizado: {user_id}")
            return jsonify({
                'success': True, 
                'message': 'Perfil atualizado com sucesso',
                'profile': updated_data
            })
            
    except Exception as e:
        logger.error(f"❌ Erro no perfil: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/sync', methods=['POST'])
@require_auth
def user_sync():
    """PROTEGIDA - Sincronizar dados"""
    user_info = request.current_user
    user_id = user_info['uid']

    try:
        data = request.get_json()
        
        # Carregar dados existentes
        stored_data = user_info.copy()
        if db_manager:
            try:
                existing_data = db_manager.get_user_data(user_id)
                if existing_data:
                    stored_data.update(existing_data)
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao carregar dados: {db_error}")
        
        # Atualizar apenas campos permitidos
        allowed_updates = ['name', 'picture', 'preferences', 'game_data']
        updated = False
        
        for field in allowed_updates:
            if field in data:
                stored_data[field] = data[field]
                updated = True
        
        if updated:
            stored_data['last_activity'] = datetime.now().isoformat()
            
            if db_manager:
                try:
                    db_manager.save_user_data(user_id, stored_data)
                    logger.info(f"✅ Dados sincronizados para: {user_id}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar dados: {db_error}")
        
        return jsonify({'success': True, 'user': stored_data})
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

# ========== API DO JOGO (PROTEGIDAS) ==========

@app.route('/api/game/state', methods=['GET', 'POST'])
@require_auth
def game_state():
    """PROTEGIDA - Obter ou salvar estado do jogo"""
    user_info = request.current_user
    user_id = user_info['uid']

    try:
        if request.method == 'GET':
            # Carregar estado do jogo
            game_data = {}
            
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
            
        else:  # POST - Salvar estado
            data = request.get_json()
            
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
                    # Carregar dados existentes
                    user_data = db_manager.get_user_data(user_id) or {}
                    user_data['game_data'] = data
                    user_data['last_activity'] = datetime.now().isoformat()
                    
                    db_manager.save_user_data(user_id, user_data)
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar no banco: {db_error}")
            
            return jsonify({'success': save_success})
            
    except Exception as e:
        logger.error(f"❌ Erro no game_state: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/ranking', methods=['GET'])
def get_ranking():
    """Ranking - PÚBLICA"""
    try:
        if db_manager:
            ranking = db_manager.get_ranking()
            return jsonify({'success': True, 'ranking': ranking})
        else:
            # Ranking mock para testes
            mock_ranking = [
                {'uid': 'user_1', 'name': 'Jogador Top', 'total_coins': 15000, 'level': 15},
                {'uid': 'user_2', 'name': 'Clique Mestre', 'total_coins': 12000, 'level': 12},
                {'uid': 'user_3', 'name': 'Iniciante', 'total_coins': 8000, 'level': 10}
            ]
            return jsonify({'success': True, 'ranking': mock_ranking})
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter ranking: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

# ========== ROTAS DO SISTEMA ==========

@app.route('/healthz')
def health_check():
    """Health check para Render"""
    return 'OK'

@app.route('/api/system/health')
def system_health():
    """Health check completo do sistema"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'authentication': 'available' if auth_manager else 'unavailable',
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