import os
import json
import time
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

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
    print("✅ AuthManager carregado")
except Exception as e:
    print(f"⚠️ AuthManager não disponível: {e}")
    auth_manager = None

try:
    from game.game_logic import GameManager
    game_manager = GameManager()
    print("✅ GameManager carregado")
except Exception as e:
    print(f"⚠️ GameManager não disponível: {e}")
    game_manager = None

try:
    from database.db_models import init_db
    init_db()
    print("✅ Database inicializado")
except Exception as e:
    print(f"⚠️ Database não disponível: {e}")

@app.before_request
def make_session_permanent():
    session.permanent = True
    session.modified = True

@app.route('/')
def index():
    """Página inicial"""
    user_info = session.get('user')
    print(f"🏠 Página inicial - Sessão: {user_info}")
    
    # Se usuário já está autenticado, redirecionar para o jogo
    if user_info:
        print("🔄 Usuário autenticado na página inicial, redirecionando...")
        return redirect('/game')
    
    return render_template('index.html', firebase_config=FIREBASE_CONFIG)

@app.route('/game')
def game():
    """Página principal do jogo"""
    user_info = session.get('user')
    print(f"🎮 Página do jogo - Sessão: {user_info}")
    
    if not user_info:
        print("❌ Usuário não autenticado, redirecionando para index")
        return redirect('/')
    
    return render_template('game.html', firebase_config=FIREBASE_CONFIG)

# ========== API ROUTES ==========

@app.route('/api/auth/status')
def auth_status():
    """Verificar status de autenticação"""
    try:
        user_info = session.get('user')
        print(f"📡 Verificando status - Sessão: {user_info}")
        
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
        print(f"❌ Erro em auth_status: {e}")
        return jsonify({'authenticated': False, 'user': None})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Processar login"""
    if not auth_manager:
        return jsonify({'error': 'Sistema de autenticação não disponível'}), 503
    
    try:
        data = request.get_json()
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Token não fornecido'}), 400

        print("🔐 Verificando token Firebase...")
        user_info = auth_manager.verify_firebase_token(token)
        
        if user_info:
            # Configurar sessão
            session['user'] = user_info
            session['user_id'] = user_info['uid']  # Aqui está correto
            session.modified = True
            
            # CORREÇÃO: Mudar 'user_id' para 'uid' no print
            print(f"✅ Login bem-sucedido: {user_info['uid']}")  # ← LINHA CORRIGIDA
            
            return jsonify({
                'success': True,
                'user': user_info,
                'message': 'Login realizado com sucesso'
            })
        else:
            print("❌ Token inválido")
            return jsonify({'error': 'Token inválido ou expirado'}), 401
            
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return jsonify({'error': 'Erro interno no servidor'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Fazer logout completo"""
    try:
        session.clear()
        print("✅ Logout realizado")
        return jsonify({'success': True, 'message': 'Logout realizado'})
    except Exception as e:
        print(f"❌ Erro no logout: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/game/state', methods=['GET', 'POST'])
def game_state():
    """Obter ou salvar estado do jogo"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    user_id = user_info['uid']  # Aqui está correto

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
            game_manager.save_game_state(user_id, data)
            return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Erro no game_state: {e}")
        return jsonify({'error': str(e)}), 500

# ========== SYSTEM ROUTES ==========

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)