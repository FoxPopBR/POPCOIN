import os
import json
import time
import logging
import urllib.parse  # <--- ADICIONAR ESTA LINHA
from datetime import timedelta, datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-popcoin-32-chars-here')
app.permanent_session_lifetime = timedelta(days=7)

# Configuração FIXA do Firebase - SEM variáveis de ambiente
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4",
    "authDomain": "popcoin-idle-829ae.firebaseapp.com", 
    "projectId": "popcoin-idle-829ae",
    "storageBucket": "popcoin-idle-829ae.firebasestorage.app",
    "messagingSenderId": "337350823197",
    "appId": "1:337350823197:web:4928ae4827e21c585da5f4"
}

# Tentar importar os managers com fallback
try:
    from auth.auth_manager import AuthManager
    auth_manager = AuthManager()
    logger.info("✅ AuthManager carregado")
except Exception as e:
    logger.warning(f"⚠️ AuthManager não disponível: {e}")
    auth_manager = None

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

@app.before_request
def make_session_permanent():
    session.permanent = True
    session.modified = True

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página inicial"""
    user_info = session.get('user')
    logger.info(f"🏠 Página inicial - Sessão: {user_info}")
    
    # Se usuário já está autenticado, redirecionar para o jogo
    if user_info:
        logger.info("🔄 Usuário autenticado na página inicial, redirecionando...")
        return redirect('/game')
    
    return render_template('index.html', firebase_config=FIREBASE_CONFIG)

@app.route('/game')
def game():
    """Página principal do jogo"""
    user_info = session.get('user')
    logger.info(f"🎮 Página do jogo - Sessão: {user_info}")
    
    if not user_info:
        logger.warning("❌ Usuário não autenticado, redirecionando para index")
        return redirect('/')
    
    return render_template('game.html', firebase_config=FIREBASE_CONFIG)

@app.route('/profile')
def profile():
    """Página de perfil do usuário"""
    user_info = session.get('user')
    logger.info(f"👤 Página de perfil - Sessão: {user_info}")
    
    if not user_info:
        logger.warning("❌ Usuário não autenticado, redirecionando para index")
        return redirect('/')
    
    return render_template('profile.html', firebase_config=FIREBASE_CONFIG)

@app.route('/api/debug/database')
def debug_database():
    """Debug da conexão com banco de dados"""
    try:
        database_url = os.environ.get('DATABASE_URL', 'Não configurada')
        
        # Informações seguras (sem senha)
        safe_url = "Não disponível"
        if database_url and database_url != 'Não configurada':
            parsed = urllib.parse.urlparse(database_url)
            safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
        
        return jsonify({
            'database_configured': bool(database_url and database_url != 'Não configurada'),
            'database_url_safe': safe_url,
            'db_manager_initialized': db_manager.initialized if db_manager else False,
            'environment_keys': list(os.environ.keys())
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# ========== API DE AUTENTICAÇÃO ==========

@app.route('/api/auth/status')
def auth_status():
    """Verificar status de autenticação"""
    try:
        user_info = session.get('user')
        logger.info(f"📡 Verificando status - Sessão: {user_info}")
        
        if user_info:
            return jsonify({
                'authenticated': True,
                'user': user_info
            })
        else:
            return jsonify({
                'authenticated': False,
                'user': None
            })
    except Exception as e:
        logger.error(f"❌ Erro em auth_status: {e}")
        return jsonify({'authenticated': False, 'user': None})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Processar login com token do Firebase"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400

        logger.info("🔐 Verificando token Firebase...")
        user_info = auth_manager.verify_firebase_token(token)
        
        if user_info:
            # Inicializar estrutura completa do usuário na sessão
            session_user_data = {
                'uid': user_info['uid'],
                'email': user_info['email'],
                'name': user_info.get('name', user_info['email'].split('@')[0]),
                'picture': user_info.get('picture'),
                'email_verified': user_info.get('email_verified', False),
                'created_at': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat(),
                'game_data': {
                    'popcoins': 0,
                    'clicks': 0,
                    'level': 1,
                    'experience': 0
                },
                'preferences': {
                    'notifications': True,
                    'sound_effects': True,
                    'music': True
                }
            }
            
            # Tentar carregar dados existentes do usuário
            if db_manager:
                try:
                    existing_data = db_manager.get_user_data(user_info['uid'])
                    if existing_data:
                        session_user_data.update(existing_data)
                        logger.info(f"✅ Dados existentes carregados para: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao carregar dados do usuário: {db_error}")
            
            # Configurar sessão
            session['user'] = session_user_data
            session['user_id'] = user_info['uid']
            session.modified = True
            
            # Salvar dados no banco se disponível
            if db_manager:
                try:
                    db_manager.save_user_data(user_info['uid'], session_user_data)
                    logger.info(f"✅ Dados salvos no banco para: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar dados no banco: {db_error}")
            
            logger.info(f"✅ Login bem-sucedido: {user_info['uid']}")
            
            return jsonify({
                'success': True,
                'user': session_user_data,
                'message': 'Login realizado com sucesso'
            })
        else:
            logger.warning("❌ Token inválido")
            return jsonify({'error': 'Token inválido ou expirado'}), 401
            
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Fazer logout completo"""
    try:
        user_info = session.get('user')
        if user_info and db_manager:
            # Salvar dados antes de fazer logout
            try:
                db_manager.save_user_data(user_info['uid'], user_info)
                logger.info(f"💾 Dados salvos antes do logout: {user_info['uid']}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar dados no logout: {db_error}")
        
        session.clear()
        logger.info("✅ Logout realizado")
        return jsonify({'success': True, 'message': 'Logout realizado'})
    except Exception as e:
        logger.error(f"❌ Erro no logout: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/verify', methods=['POST'])
def auth_verify():
    """Verificar token do Firebase (para requisições autenticadas)"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token não fornecido'}), 401
            
        token = auth_header.split('Bearer ')[1]
        user_info = auth_manager.verify_firebase_token(token)
        
        if user_info:
            return jsonify({
                'authenticated': True,
                'user': user_info
            })
        else:
            return jsonify({'authenticated': False}), 401
            
    except Exception as e:
        logger.error(f"❌ Erro na verificação: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

# ========== API DE USUÁRIO E PERFIL ==========

@app.route('/api/user/sync', methods=['POST'])
def user_sync():
    """Sincronizar dados do usuário com informações atualizadas do Firebase"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token não fornecido'}), 401
            
        token = auth_header.split('Bearer ')[1]
        user_info = auth_manager.verify_firebase_token(token)
        
        if not user_info:
            return jsonify({'error': 'Token inválido'}), 401
        
        # Obter dados da sessão atual
        session_user = session.get('user')
        if not session_user:
            return jsonify({'error': 'Sessão não encontrada'}), 401
        
        # Atualizar dados do usuário com informações do Firebase
        session_user.update({
            'name': user_info.get('name', session_user.get('name')),
            'picture': user_info.get('picture', session_user.get('picture')),
            'email_verified': user_info.get('email_verified', session_user.get('email_verified', False)),
            'last_login': datetime.now().isoformat()
        })
        
        session['user'] = session_user
        session.modified = True
        
        # Salvar no banco se disponível
        if db_manager:
            try:
                db_manager.save_user_data(user_info['uid'], session_user)
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar dados na sincronização: {db_error}")
        
        logger.info(f"✅ Dados sincronizados para: {user_info['uid']}")
        return jsonify({'success': True, 'user': session_user})
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/profile', methods=['GET', 'PUT'])
def user_profile():
    """Obter ou atualizar perfil do usuário"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    try:
        if request.method == 'GET':
            # Retornar perfil completo do usuário
            return jsonify({
                'success': True, 
                'profile': user_info
            })
            
        elif request.method == 'PUT':
            # Atualizar perfil do usuário
            data = request.get_json()
            
            # Campos permitidos para atualização
            allowed_fields = ['name', 'preferences']
            updates = {}
            
            for field in allowed_fields:
                if field in data:
                    if field == 'preferences':
                        # Mesclar preferências em vez de substituir
                        current_prefs = user_info.get('preferences', {})
                        current_prefs.update(data['preferences'])
                        updates['preferences'] = current_prefs
                    else:
                        updates[field] = data[field]
            
            # Aplicar atualizações
            user_info.update(updates)
            user_info['updated_at'] = datetime.now().isoformat()
            
            session['user'] = user_info
            session.modified = True
            
            # Salvar no banco se disponível
            if db_manager:
                try:
                    db_manager.save_user_data(user_info['uid'], user_info)
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar perfil no banco: {db_error}")
            
            logger.info(f"✅ Perfil atualizado: {user_info['uid']}")
            return jsonify({
                'success': True, 
                'message': 'Perfil atualizado com sucesso',
                'profile': user_info
            })
            
    except Exception as e:
        logger.error(f"❌ Erro no perfil: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/create', methods=['POST'])
def user_create():
    """Criar perfil de usuário (para novos registros)"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token não fornecido'}), 401
            
        token = auth_header.split('Bearer ')[1]
        user_info = auth_manager.verify_firebase_token(token)
        
        if not user_info:
            return jsonify({'error': 'Token inválido'}), 401
        
        data = request.get_json()
        
        # Criar estrutura completa do usuário
        new_user_data = {
            'uid': user_info['uid'],
            'email': user_info['email'],
            'name': data.get('name', user_info.get('name', user_info['email'].split('@')[0])),
            'picture': data.get('photo_url', user_info.get('picture')),
            'email_verified': user_info.get('email_verified', False),
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat(),
            'game_data': {
                'popcoins': 0,
                'clicks': 0,
                'level': 1,
                'experience': 0
            },
            'preferences': {
                'notifications': True,
                'sound_effects': True,
                'music': True
            }
        }
        
        # Configurar sessão
        session['user'] = new_user_data
        session['user_id'] = user_info['uid']
        session.modified = True
        
        # Salvar no banco se disponível
        if db_manager:
            try:
                db_manager.save_user_data(user_info['uid'], new_user_data)
                logger.info(f"✅ Novo usuário criado no banco: {user_info['uid']}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao criar usuário no banco: {db_error}")
        
        logger.info(f"✅ Novo perfil criado: {user_info['uid']}")
        return jsonify({
            'success': True,
            'message': 'Perfil criado com sucesso',
            'profile': new_user_data
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar usuário: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

# ========== API DO JOGO ==========

@app.route('/api/game/state', methods=['GET', 'POST'])
def game_state():
    """Obter ou salvar estado do jogo"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    user_id = user_info['uid']

    if not game_manager:
        # Retornar estado padrão se game_manager não estiver disponível
        default_state = {
            'coins': 0,
            'coins_per_click': 1,
            'coins_per_second': 0,
            'total_coins': 0,
            'prestige_level': 0,
            'upgrades': {
                'click_power': 1,
                'auto_clickers': 0,
                'click_bots': 0
            }
        }
        
        if request.method == 'GET':
            return jsonify(default_state)
        else:
            return jsonify({'success': True})

    try:
        if request.method == 'GET':
            game_state = game_manager.get_user_game_state(user_id)
            return jsonify(game_state)
        else:
            data = request.get_json()
            success = game_manager.save_game_state(user_id, data)
            return jsonify({'success': success})
    except Exception as e:
        logger.error(f"❌ Erro no game_state: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/ranking', methods=['GET'])
def get_ranking():
    """Obter ranking de jogadores"""
    try:
        if db_manager:
            ranking = db_manager.get_ranking()
            return jsonify({'success': True, 'ranking': ranking})
        else:
            # Ranking mock para desenvolvimento
            mock_ranking = [
                {'uid': 'user_1', 'name': 'Jogador Top', 'popcoins': 15000, 'level': 15},
                {'uid': 'user_2', 'name': 'Clique Mestre', 'popcoins': 12000, 'level': 12},
                {'uid': 'user_3', 'name': 'Coletor Ávido', 'popcoins': 8000, 'level': 10}
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
            'database': 'available' if db_manager else 'unavailable',
            'firebase': 'configured'
        }
    })

@app.route('/debug/session')
def debug_session():
    """Debug da sessão"""
    session_info = {
        'session_exists': bool(session),
        'user_in_session': session.get('user'),
        'user_id_in_session': session.get('user_id'),
        'session_keys': list(session.keys())
    }
    return jsonify(session_info)

@app.route('/debug/firebase')
def debug_firebase():
    """Debug do Firebase"""
    return jsonify({
        'firebase_configured': True,
        'config_keys': list(FIREBASE_CONFIG.keys()) if FIREBASE_CONFIG else None
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
    
    logger.info(f"🚀 Iniciando PopCoin IDLE na porta {port} (debug: {debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)