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

# ✅ CONFIGURAÇÃO DE SESSÃO: 1 hora de inatividade, sessão não-permanente
app.permanent_session_lifetime = timedelta(hours=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

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

@app.before_request
def check_session_and_security():
    """✅ VERIFICAÇÃO CENTRALIZADA: Sessão e segurança em cada requisição"""
    # Não usar sessões permanentes - fechar janela = logout
    session.permanent = False
    
    # Verificar se usuário está na sessão
    if session.get('user'):
        user_info = session['user']
        last_activity = user_info.get('last_activity')
        
        # ✅ VERIFICAÇÃO DE INATIVIDADE: 1 hora sem atividade = logout
        if last_activity:
            try:
                last_activity_time = datetime.fromisoformat(last_activity)
                inactivity_period = (datetime.now() - last_activity_time).total_seconds()
                
                if inactivity_period > 3600:  # 1 hora em segundos
                    logger.info(f"🕐 Sessão expirada por inatividade: {user_info.get('email')}")
                    session.clear()
                    return  # Não redirecionar para evitar loops
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar inatividade: {e}")
                session.clear()
                return
        
        # ✅ ATUALIZAR última atividade
        user_info['last_activity'] = datetime.now().isoformat()
        session['user'] = user_info
        session.modified = True

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página inicial - sempre começa deslogado"""
    logger.info("🏠 Página inicial - Verificando sessão...")
    
    user_info = session.get('user')
    firebase_config = get_firebase_config()
    
    logger.info(f"🏠 Página inicial - Usuário: {'Logado' if user_info else 'Deslogado'}")
    
    return render_template('index.html', 
                         firebase_config=firebase_config,
                         user=user_info)

@app.route('/game')
def game():
    """Página principal do jogo - REQUER AUTENTICAÇÃO"""
    user_info = session.get('user')
    
    if not user_info:
        logger.warning("❌ Acesso não autorizado ao jogo - redirecionando para login")
        return redirect('/')
    
    logger.info(f"🎮 Acesso autorizado ao jogo: {user_info.get('email')}")
    firebase_config = get_firebase_config()
    
    return render_template('game.html', 
                         firebase_config=firebase_config,
                         user=user_info)

@app.route('/profile')
def profile():
    """Página de perfil - DESTINO PRINCIPAL APÓS LOGIN"""
    user_info = session.get('user')
    
    if not user_info:
        logger.warning("❌ Acesso não autorizado ao perfil - redirecionando para login")
        return redirect('/')
    
    logger.info(f"👤 Acesso autorizado ao perfil: {user_info.get('email')}")
    firebase_config = get_firebase_config()
    
    return render_template('profile.html', 
                         firebase_config=firebase_config, 
                         user=user_info)

# ========== API DE AUTENTICAÇÃO ==========

@app.route('/api/auth/status')
def auth_status():
    """Verificar status de autenticação - SIMPLIFICADO"""
    try:
        user_info = session.get('user')
        
        if user_info:
            # ✅ Atualizar atividade apenas se estiver logado
            user_info['last_activity'] = datetime.now().isoformat()
            session['user'] = user_info
            session.modified = True
            
            logger.debug(f"📡 Status: Usuário logado - {user_info.get('email')}")
            return jsonify({
                'authenticated': True,
                'user': user_info
            })
        else:
            logger.debug("📡 Status: Usuário deslogado")
            return jsonify({
                'authenticated': False,
                'user': None
            })
            
    except Exception as e:
        logger.error(f"❌ Erro em auth_status: {e}")
        return jsonify({'authenticated': False, 'user': None})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Processar login com token do Firebase - OTIMIZADO"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        # ✅ VERIFICAR SE JÁ ESTÁ LOGADO para evitar múltiplos logins
        existing_user = session.get('user')
        if existing_user:
            logger.info(f"🔄 Usuário já logado: {existing_user.get('email')}")
            return jsonify({
                'success': True,
                'user': existing_user,
                'message': 'Já autenticado',
                'redirect_to': '/profile'
            })

        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400

        logger.info("🔐 Verificando token Firebase...")
        user_info = auth_manager.verify_firebase_token(token)
        
        if user_info:
            current_time = datetime.now().isoformat()
            
            # ✅ DADOS BÁSICOS DO USUÁRIO
            session_user_data = {
                'uid': user_info['uid'],
                'email': user_info['email'],
                'name': user_info.get('name', user_info['email'].split('@')[0]),
                'picture': user_info.get('picture', '/static/images/default-avatar.png'),
                'email_verified': user_info.get('email_verified', False),
                'created_at': current_time,
                'last_login': current_time,
                'last_activity': current_time  # ✅ MARCA TEMPO DE ATIVIDADE
            }
            
            # ✅ CARREGAR/CRIAR DADOS DO BANCO
            if db_manager:
                try:
                    existing_data = db_manager.get_user_data(user_info['uid'])
                    if existing_data:
                        # ✅ USUÁRIO EXISTENTE: manter dados, atualizar login
                        existing_data.update({
                            'last_login': current_time,
                            'last_activity': current_time,
                            'name': session_user_data['name'],
                            'picture': session_user_data['picture'],
                            'email_verified': session_user_data['email_verified']
                        })
                        session_user_data = existing_data
                        logger.info(f"✅ Dados existentes carregados para: {user_info['uid']}")
                    else:
                        # ✅ NOVO USUÁRIO: criar dados iniciais
                        session_user_data.update({
                            'game_data': {
                                'popcoins': 0,
                                'clicks': 0,
                                'level': 1,
                                'experience': 0,
                                'coins_per_click': 1,
                                'coins_per_second': 0,
                                'total_coins': 0,
                                'prestige_level': 0,
                                'upgrades': {
                                    'click_power': 1,
                                    'auto_clicker': 0,
                                    'auto_clickers': 0,
                                    'click_bots': 0
                                },
                                'inventory': [],
                                'achievements': []
                            },
                            'preferences': {
                                'notifications': True,
                                'sound_effects': True,
                                'music': True
                            }
                        })
                        logger.info(f"✅ Novo usuário criado: {user_info['uid']}")
                    
                    # ✅ SALVAR NO BANCO (apenas uma vez)
                    db_manager.save_user_data(user_info['uid'], session_user_data)
                    
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro no banco de dados: {db_error}")
                    # Continuar mesmo com erro no banco
            
            # ✅ CRIAR SESSÃO
            session['user'] = session_user_data
            session['user_id'] = user_info['uid']
            
            logger.info(f"✅ Login bem-sucedido: {user_info['email']}")
            
            return jsonify({
                'success': True,
                'user': session_user_data,
                'message': 'Login realizado com sucesso',
                'redirect_to': '/profile'  # ✅ DESTINO CONSISTENTE
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
        
        # ✅ SALVAR DADOS ANTES DO LOGOUT (se possível)
        if user_info and db_manager:
            try:
                db_manager.save_user_data(user_info['uid'], user_info)
                logger.info(f"💾 Dados salvos antes do logout: {user_info['uid']}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar dados no logout: {db_error}")
        
        # ✅ LIMPAR SESSÃO COMPLETAMENTE
        session.clear()
        logger.info("✅ Logout completo realizado - sessão limpa")
        
        return jsonify({
            'success': True, 
            'message': 'Logout realizado com sucesso',
            'redirect_to': '/'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no logout: {e}")
        session.clear()  # ✅ Garantir que sessão seja limpa mesmo com erro
        return jsonify({'success': True, 'message': 'Logout realizado'})

@app.route('/api/auth/firebase-config')
def get_firebase_config():
    """Fornecer configuração do Firebase para o frontend"""
    try:
        config = get_firebase_config()
        return jsonify(config)
    except Exception as e:
        logger.error(f"❌ Erro ao fornecer configuração Firebase: {e}")
        return jsonify({'error': 'Erro de configuração'}), 500

# ========== API DE USUÁRIO E PERFIL ==========

@app.route('/api/user/sync', methods=['POST'])
def user_sync():
    """Sincronizar dados do usuário - OTIMIZADO"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    try:
        data = request.get_json()
        
        # ✅ ATUALIZAR APENAS CAMPOS PERMITIDOS
        allowed_updates = ['name', 'picture', 'preferences', 'game_data']
        updated = False
        
        for field in allowed_updates:
            if field in data and data[field] != user_info.get(field):
                user_info[field] = data[field]
                updated = True
        
        if updated:
            user_info['last_activity'] = datetime.now().isoformat()
            session['user'] = user_info
            session.modified = True
            
            if db_manager:
                try:
                    db_manager.save_user_data(user_info['uid'], user_info)
                    logger.info(f"✅ Dados sincronizados para: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar dados na sincronização: {db_error}")
        
        return jsonify({'success': True, 'user': user_info})
        
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
            user_info['last_activity'] = datetime.now().isoformat()
            
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
            
            # ✅ ATUALIZAR ATIVIDADE ao salvar estado do jogo
            if user_info:
                user_info['last_activity'] = datetime.now().isoformat()
                session['user'] = user_info
                session.modified = True
            
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
    
    user_info = session.get('user')
    
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
            'user_authenticated': bool(user_info),
            'user_email': user_info.get('email') if user_info else None,
            'last_activity': user_info.get('last_activity') if user_info else None
        }
    })

@app.route('/debug/session')
def debug_session():
    """Debug da sessão (apenas para desenvolvimento)"""
    user_info = session.get('user')
    session_info = {
        'session_exists': bool(session),
        'user_authenticated': bool(user_info),
        'user_email': user_info.get('email') if user_info else None,
        'last_activity': user_info.get('last_activity') if user_info else None,
        'session_keys': list(session.keys())
    }
    return jsonify(session_info)

@app.route('/debug/firebase')
def debug_firebase():
    """Debug do Firebase (apenas para desenvolvimento)"""
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
    logger.info(f"⏰ Configuração de sessão: 1 hora de inatividade, sessão não-permanente")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)