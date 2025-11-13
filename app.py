import os
import json
import time
import logging
import secrets
from datetime import timedelta, datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ✅ CONFIGURAÇÃO DE SESSÃO OTIMIZADA PARA JOGOS
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,  # ✅ HTTPS no Render.com
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # ✅ 7 DIAS para jogos
    SESSION_REFRESH_EACH_REQUEST=True  # ✅ RENOVAR a cada requisição
)

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

# ✅ MIDDLEWARE DE SESSÃO SIMPLIFICADO E OTIMIZADO
@app.before_request
def handle_session_management():
    """✅ SISTEMA DE SESSÃO SIMPLIFICADO - Foco em estabilidade"""
    
    # ✅ SEMPRE usar sessão permanente para jogos
    session.permanent = True
    
    paths_that_require_auth = ['/game', '/profile', '/api/game', '/api/user']
    current_path = request.path
    
    # ✅ Verificar se é uma rota que requer autenticação
    requires_auth = any(current_path.startswith(path) for path in paths_that_require_auth)
    
    # ✅ Se não tem usuário na sessão e está tentando acessar área protegida
    if requires_auth and not session.get('user'):
        logger.warning(f"🚫 Acesso não autorizado à: {current_path}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Não autenticado'}), 401
        return redirect('/')
    
    # ✅ ATUALIZAR atividade APENAS se usuário estiver logado
    user_info = session.get('user')
    if user_info:
        # ✅ Atualizar atividade a cada requisição (mais simples)
        user_info['last_activity'] = datetime.now().isoformat()
        session['user'] = user_info
        # Não forçar session.modified = True para melhor performance

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página inicial - sistema inteligente de redirecionamento"""
    logger.info("🏠 Página inicial - Verificando sessão...")
    
    user_info = session.get('user')
    firebase_config = get_firebase_config()
    
    # ✅ CORREÇÃO: Verificar se veio do /game para evitar loop
    referer = request.headers.get('Referer', '')
    coming_from_game = '/game' in referer
    
    # ✅ SE JÁ ESTIVER LOGADO, REDIRECIONAR PARA O JOGO (mas não se veio do game)
    if user_info and not coming_from_game:
        logger.info(f"🏠 Usuário já logado: {user_info.get('email')} - Redirecionando para jogo")
        return redirect('/game')
    
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
    """Página de perfil - REQUER AUTENTICAÇÃO"""
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
    """✅ VERIFICAÇÃO SIMPLES DE STATUS - sem lógica complexa"""
    try:
        user_info = session.get('user')
        
        if user_info:
            logger.debug(f"📡 Status: Usuário logado - {user_info.get('email')}")
            return jsonify({
                'authenticated': True,
                'user': {
                    'uid': user_info.get('uid'),
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'email_verified': user_info.get('email_verified', False)
                }
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
    """✅ PROCESSAR LOGIN - Versão Simplificada e Robusta"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400

        logger.info("🔐 Verificando token Firebase...")
        user_info = auth_manager.verify_firebase_token(token)
        
        if not user_info:
            logger.warning("❌ Token inválido")
            return jsonify({'error': 'Token inválido ou expirado'}), 401

        current_time = datetime.now().isoformat()
        
        # ✅ DADOS ESSENCIAIS DO USUÁRIO (minimais)
        session_user_data = {
            'uid': user_info['uid'],
            'email': user_info['email'],
            'name': user_info.get('name', user_info['email'].split('@')[0]),
            'picture': user_info.get('picture', '/static/images/default-avatar.png'),
            'email_verified': user_info.get('email_verified', False),
            'created_at': current_time,
            'last_login': current_time,
            'last_activity': current_time
        }
        
        # ✅ TENTAR CARREGAR DADOS EXISTENTES DO BANCO
        if db_manager:
            try:
                existing_data = db_manager.get_user_data(user_info['uid'])
                if existing_data:
                    # ✅ PRESERVAR dados importantes existentes
                    session_user_data.update({
                        'game_data': existing_data.get('game_data', {}),
                        'preferences': existing_data.get('preferences', {
                            'notifications': True,
                            'sound_effects': True,
                            'music': True
                        }),
                        'last_login': current_time,
                        'last_activity': current_time
                    })
                    logger.info(f"✅ Dados existentes carregados: {user_info['uid']}")
                else:
                    # ✅ DADOS INICIAIS PARA NOVO USUÁRIO
                    session_user_data.update({
                        'game_data': {
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
                        },
                        'preferences': {
                            'notifications': True,
                            'sound_effects': True,
                            'music': True
                        }
                    })
                    logger.info(f"✅ Novo usuário criado: {user_info['uid']}")
                
                # ✅ SALVAR NO BANCO
                db_manager.save_user_data(user_info['uid'], session_user_data)
                
            except Exception as db_error:
                logger.warning(f"⚠️ Erro no banco, usando dados locais: {db_error}")
                # Usar dados mínimos se o banco falhar
                if 'game_data' not in session_user_data:
                    session_user_data['game_data'] = {
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
        
        # ✅ CRIAR SESSÃO (agora permanente)
        session['user'] = session_user_data
        session['user_id'] = user_info['uid']
        
        logger.info(f"✅ Login bem-sucedido: {user_info['email']}")
        
        return jsonify({
            'success': True,
            'user': session_user_data,
            'message': 'Login realizado com sucesso'
        })
            
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """✅ LOGOUT COMPLETO - Versão Simplificada"""
    try:
        user_info = session.get('user')
        
        # ✅ SALVAR DADOS FINAIS (se possível)
        if user_info and db_manager:
            try:
                db_manager.save_user_data(user_info['uid'], user_info)
                logger.info(f"💾 Dados salvos no logout: {user_info['uid']}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar dados: {db_error}")
        
        # ✅ LIMPAR SESSÃO COMPLETAMENTE
        session.clear()
        logger.info("✅ Logout completo - sessão destruída")
        
        return jsonify({
            'success': True, 
            'message': 'Logout realizado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no logout: {e}")
        session.clear()  # ✅ Garantir limpeza mesmo com erro
        return jsonify({'success': True, 'message': 'Logout realizado'})

@app.route('/api/auth/firebase-config')
def firebase_config_api():
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
    """✅ SINCRONIZAR DADOS - Versão Otimizada"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    try:
        data = request.get_json()
        
        # ✅ ATUALIZAR APENAS CAMPOS PERMITIDOS
        allowed_updates = ['name', 'picture', 'preferences', 'game_data']
        updated = False
        
        for field in allowed_updates:
            if field in data:
                user_info[field] = data[field]
                updated = True
        
        if updated:
            user_info['last_activity'] = datetime.now().isoformat()
            session['user'] = user_info
            
            if db_manager:
                try:
                    db_manager.save_user_data(user_info['uid'], user_info)
                    logger.info(f"✅ Dados sincronizados para: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar dados: {db_error}")
        
        return jsonify({'success': True, 'user': user_info})
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/profile', methods=['GET', 'PUT'])
def user_profile():
    """✅ OBTER OU ATUALIZAR PERFIL - Versão Simplificada"""
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
            
            # ✅ CAMPOS PERMITIDOS PARA ATUALIZAÇÃO
            allowed_fields = ['name', 'preferences']
            
            for field in allowed_fields:
                if field in data:
                    user_info[field] = data[field]
            
            user_info['last_activity'] = datetime.now().isoformat()
            session['user'] = user_info
            
            # ✅ SALVAR NO BANCO
            if db_manager:
                try:
                    db_manager.save_user_data(user_info['uid'], user_info)
                    logger.info(f"✅ Perfil salvo no banco: {user_info['uid']}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar perfil: {db_error}")
            
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
    """✅ OBTER OU SALVAR ESTADO DO JOGO - Versão Robusta"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    user_id = user_info['uid']

    try:
        if request.method == 'GET':
            # ✅ PRIORIDADE: Dados da sessão primeiro
            game_data = user_info.get('game_data', {})
            
            # ✅ SE game_manager disponível, tentar carregar do banco
            if game_manager and not game_data:
                try:
                    game_data = game_manager.get_user_game_state(user_id)
                    # ✅ ATUALIZAR sessão com dados do banco
                    user_info['game_data'] = game_data
                    session['user'] = user_info
                except Exception as mgr_error:
                    logger.warning(f"⚠️ Erro no game_manager: {mgr_error}")
            
            return jsonify(game_data)
            
        else:  # POST - Salvar estado
            data = request.get_json()
            
            # ✅ ATUALIZAR DADOS DO JOGO NA SESSÃO
            user_info['game_data'] = data
            user_info['last_activity'] = datetime.now().isoformat()
            session['user'] = user_info
            
            # ✅ SALVAR NO BANCO (se disponível)
            save_success = True
            if game_manager:
                try:
                    save_success = game_manager.save_game_state(user_id, data)
                except Exception as mgr_error:
                    logger.warning(f"⚠️ Erro ao salvar no game_manager: {mgr_error}")
                    save_success = False
            
            # ✅ SALVAR NO db_manager também
            if db_manager:
                try:
                    db_manager.save_user_data(user_id, user_info)
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar no banco: {db_error}")
            
            return jsonify({'success': save_success})
            
    except Exception as e:
        logger.error(f"❌ Erro no game_state: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/user/ranking', methods=['GET'])
def get_ranking():
    """Obter ranking de jogadores"""
    try:
        if db_manager:
            ranking = db_manager.get_ranking()
            return jsonify({'success': True, 'ranking': ranking})
        else:
            # ✅ RANKING MOCK PARA TESTES
            user_info = session.get('user')
            mock_ranking = [
                {'uid': 'user_1', 'name': 'Jogador Top', 'total_coins': 15000, 'level': 15},
                {'uid': 'user_2', 'name': 'Clique Mestre', 'total_coins': 12000, 'level': 12},
                {'uid': user_info.get('uid') if user_info else 'user_3', 
                 'name': user_info.get('name') if user_info else 'Você', 
                 'total_coins': user_info.get('game_data', {}).get('total_coins', 0) if user_info else 8000, 
                 'level': 10}
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
    user_info = session.get('user')
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'authentication': 'available' if auth_manager else 'unavailable',
            'game_system': 'available' if game_manager else 'unavailable',
            'database': 'available' if db_manager else 'unavailable'
        },
        'session': {
            'user_authenticated': bool(user_info),
            'user_email': user_info.get('email') if user_info else None
        }
    })

@app.route('/debug/session')
def debug_session():
    """✅ DEBUG DA SESSÃO - Para desenvolvimento"""
    user_info = session.get('user')
    session_info = {
        'session_exists': bool(session),
        'user_authenticated': bool(user_info),
        'user_email': user_info.get('email') if user_info else None,
        'last_activity': user_info.get('last_activity') if user_info else None,
        'session_keys': list(session.keys()),
        'game_data_keys': list(user_info.get('game_data', {}).keys()) if user_info else []
    }
    return jsonify(session_info)

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
    logger.info(f"⏰ Sistema de sessão: 7 dias de duração")
    logger.info(f"🔄 Sessão permanente: Mantém login entre abas/navegador")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)