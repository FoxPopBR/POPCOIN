import os
import json
import time
import logging
import urllib.parse
from datetime import timedelta, datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-popcoin-32-chars-here')

# ✅ CORREÇÃO: Sessões temporárias (4 horas) em vez de permanentes
app.permanent_session_lifetime = timedelta(hours=4)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

# ✅ CORREÇÃO: Remover configuração Firebase hardcoded - usar auth_manager

# Importar managers
try:
    from auth.auth_manager import auth_manager
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
def check_session_security():
    """Verificação de segurança em cada requisição"""
    session.permanent = False
    
    if session.get('user'):
        user_info = session['user']
        last_login = user_info.get('last_login')
        
        if last_login:
            try:
                login_time = datetime.fromisoformat(last_login)
                if (datetime.now() - login_time).total_seconds() > 4 * 3600:
                    logger.warning(f"🕐 Sessão expirada para: {user_info.get('email')}")
                    session.clear()
                    return redirect('/')
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar tempo de sessão: {e}")
                session.clear()
                return redirect('/')

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página inicial - sempre usuário deslogado ao iniciar servidor"""
    logger.info("🏠 Página inicial - Verificando sessão...")
    
    user_info = session.get('user')
    if user_info:
        last_login = user_info.get('last_login')
        if last_login:
            try:
                login_time = datetime.fromisoformat(last_login)
                if (datetime.now() - login_time).total_seconds() > 4 * 3600:
                    logger.info("🕐 Sessão expirada na página inicial, limpando...")
                    session.clear()
                    user_info = None
            except:
                session.clear()
                user_info = None
    
    firebase_config = {}
    if auth_manager:
        try:
            firebase_config = auth_manager.get_firebase_config_for_frontend()
            logger.info("✅ Configuração Firebase obtida do auth_manager")
        except Exception as e:
            logger.error(f"❌ Erro ao obter configuração Firebase: {e}")
    
    logger.info(f"🏠 Página inicial - Usuário: {'Logado' if user_info else 'Deslogado'}")
    
    return render_template('index.html', firebase_config=firebase_config)

@app.route('/game')
def game():
    """Página principal do jogo - REQUER AUTENTICAÇÃO"""
    user_info = session.get('user')
    logger.info(f"🎮 Página do jogo - Sessão: {user_info}")
    
    if not user_info:
        logger.warning("❌ Acesso não autorizado ao jogo, redirecionando...")
        return redirect('/')
    
    firebase_config = {}
    if auth_manager:
        try:
            firebase_config = auth_manager.get_firebase_config_for_frontend()
        except Exception as e:
            logger.error(f"❌ Erro ao obter configuração Firebase: {e}")
    
    return render_template('game.html', firebase_config=firebase_config)

@app.route('/profile')
def profile():
    """Página de perfil - DESTINO PRINCIPAL APÓS LOGIN"""
    user_info = session.get('user')
    logger.info(f"👤 Página de perfil - Sessão: {user_info}")
    
    if not user_info:
        logger.warning("❌ Acesso não autorizado ao perfil, redirecionando...")
        return redirect('/')
    
    firebase_config = {}
    if auth_manager:
        try:
            firebase_config = auth_manager.get_firebase_config_for_frontend()
        except Exception as e:
            logger.error(f"❌ Erro ao obter configuração Firebase: {e}")
    
    return render_template('profile.html', firebase_config=firebase_config, user=user_info)

# ========== API DE AUTENTICAÇÃO ==========

@app.route('/api/auth/status')
def auth_status():
    """Verificar status de autenticação"""
    try:
        user_info = session.get('user')
        
        if user_info and user_info.get('last_login'):
            try:
                login_time = datetime.fromisoformat(user_info['last_login'])
                if (datetime.now() - login_time).total_seconds() > 4 * 3600:
                    logger.info("🕐 Sessão expirada no status check")
                    session.clear()
                    user_info = None
            except:
                session.clear()
                user_info = None
        
        logger.info(f"📡 Status de autenticação: {'Logado' if user_info else 'Deslogado'}")
        
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
            current_time = datetime.now().isoformat()
            
            session_user_data = {
                'uid': user_info['uid'],
                'email': user_info['email'],
                'name': user_info.get('name', user_info['email'].split('@')[0]),
                'picture': user_info.get('picture', '/static/images/default-avatar.png'),
                'email_verified': user_info.get('email_verified', False),
                'created_at': current_time,
                'last_login': current_time,
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
            
            if db_manager:
                try:
                    existing_data = db_manager.get_user_data(user_info['uid'])
                    if existing_data:
                        existing_data['last_login'] = current_time
                        session_user_data.update(existing_data)
                        logger.info(f"✅ Dados existentes carregados para: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao carregar dados do usuário: {db_error}")
            
            session['user'] = session_user_data
            session['user_id'] = user_info['uid']
            session.modified = True
            
            if db_manager:
                try:
                    db_manager.save_user_data(user_info['uid'], session_user_data)
                    logger.info(f"✅ Dados salvos no banco para: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar dados no banco: {db_error}")
            
            logger.info(f"✅ Login bem-sucedido: {user_info['email']}")
            
            return jsonify({
                'success': True,
                'user': session_user_data,
                'message': 'Login realizado com sucesso',
                'redirect_to': '/profile'
            })
        else:
            logger.warning("❌ Token inválido")
            return jsonify({'error': 'Token inválido ou expirado'}), 401
            
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Fazer logout COMPLETO"""
    try:
        user_info = session.get('user')
        if user_info and db_manager:
            try:
                db_manager.save_user_data(user_info['uid'], user_info)
                logger.info(f"💾 Dados salvos antes do logout: {user_info['uid']}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar dados no logout: {db_error}")
        
        session.clear()
        logger.info("✅ Logout completo realizado - sessão limpa")
        return jsonify({'success': True, 'message': 'Logout realizado com sucesso'})
    except Exception as e:
        logger.error(f"❌ Erro no logout: {e}")
        session.clear()
        return jsonify({'success': True, 'message': 'Logout realizado'})

@app.route('/api/auth/firebase-config')
def get_firebase_config():
    """Fornecer configuração do Firebase para o frontend de forma segura"""
    try:
        if auth_manager:
            config = auth_manager.get_firebase_config_for_frontend()
            logger.info("✅ Configuração Firebase fornecida para frontend")
            return jsonify(config)
        else:
            logger.error("❌ AuthManager não disponível para configuração")
            return jsonify({'error': 'Configuração não disponível'}), 503
    except Exception as e:
        logger.error(f"❌ Erro ao fornecer configuração Firebase: {e}")
        return jsonify({'error': 'Erro de configuração'}), 500

# ========== API DE USUÁRIO E PERFIL ==========

@app.route('/api/user/sync', methods=['POST'])
def user_sync():
    """Sincronizar dados do usuário"""
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
        
        session_user = session.get('user')
        if not session_user:
            return jsonify({'error': 'Sessão não encontrada'}), 401
        
        session_user.update({
            'name': user_info.get('name', session_user.get('name')),
            'picture': user_info.get('picture', session_user.get('picture')),
            'email_verified': user_info.get('email_verified', session_user.get('email_verified', False)),
            'last_login': datetime.now().isoformat()
        })
        
        session['user'] = session_user
        session.modified = True
        
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
            return jsonify({
                'success': True, 
                'profile': user_info
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            allowed_fields = ['name', 'preferences']
            updates = {}
            
            for field in allowed_fields:
                if field in data:
                    if field == 'preferences':
                        current_prefs = user_info.get('preferences', {})
                        current_prefs.update(data['preferences'])
                        updates['preferences'] = current_prefs
                    else:
                        updates[field] = data[field]
            
            user_info.update(updates)
            user_info['updated_at'] = datetime.now().isoformat()
            
            session['user'] = user_info
            session.modified = True
            
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

# ========== API DO JOGO ==========

@app.route('/api/game/state', methods=['GET', 'POST'])
def game_state():
    """Obter ou salvar estado do jogo"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    user_id = user_info['uid']

    if not game_manager:
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
    firebase_status = {}
    if auth_manager:
        firebase_status = auth_manager.get_status()
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'authentication': 'available' if auth_manager else 'unavailable',
            'game_system': 'available' if game_manager else 'unavailable',
            'database': 'available' if db_manager else 'unavailable',
            'firebase': firebase_status
        },
        'session': {
            'user_authenticated': bool(session.get('user')),
            'session_keys': list(session.keys())
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
    if auth_manager:
        status = auth_manager.get_status()
        return jsonify({
            'firebase_configured': True,
            'status': status
        })
    else:
        return jsonify({
            'firebase_configured': False,
            'error': 'AuthManager não disponível'
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
    logger.info(f"🔐 Configuração de sessão: {app.permanent_session_lifetime}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)