import os
import json
import time
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from auth.auth_manager import AuthManager
from game.game_logic import GameManager
from database.db_models import init_db, get_db_connection

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-32-chars-aqui-12345')
app.permanent_session_lifetime = timedelta(days=7)

# Configurações do Firebase
FIREBASE_CONFIG = {
    "apiKey": os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY', 'AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4'),
    "authDomain": os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'popcoin-idle-829ae.firebaseapp.com'),
    "projectId": os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID', 'popcoin-idle-829ae'),
    "storageBucket": os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET', 'popcoin-idle-829ae.firebasestorage.app'),
    "messagingSenderId": os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID', '337350823197'),
    "appId": os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID', '1:337350823197:web:4928ae4827e21c585da5f4')
}

# Inicializar managers
try:
    auth_manager = AuthManager()
    print("✅ AuthManager carregado")
except Exception as e:
    print(f"❌ Erro ao carregar AuthManager: {e}")
    auth_manager = None

try:
    game_manager = GameManager()
    print("✅ GameManager carregado")
except Exception as e:
    print(f"❌ Erro ao carregar GameManager: {e}")
    game_manager = None

# Inicializar banco de dados
init_db()

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
        return redirect(url_for('game'))
    
    return render_template('index.html', firebase_config=FIREBASE_CONFIG)

@app.route('/game')
def game():
    """Página principal do jogo"""
    user_info = session.get('user')
    print(f"🎮 Página do jogo - Sessão: {user_info}")
    
    if not user_info:
        print("❌ Usuário não autenticado, redirecionando para index")
        return redirect(url_for('index'))
    
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
            # Limpar sessão se não autenticado
            session.pop('user_id', None)
            session.pop('user', None)
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
            session['user_id'] = user_info['user_id']
            session.modified = True
            
            print(f"✅ Login bem-sucedido: {user_info['user_id']}")
            return jsonify({
                'success': True,
                'user': user_info,
                'message': 'Login realizado com sucesso'
            })
        else:
            print("❌ Token inválido")
            session.clear()
            return jsonify({'error': 'Token inválido ou expirado'}), 401
            
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        session.clear()
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

    user_id = user_info['user_id']

    if not game_manager:
        return jsonify({'error': 'Sistema de jogo não disponível'}), 503

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

@app.route('/api/game/upgrade', methods=['POST'])
def game_upgrade():
    """Comprar upgrade"""
    user_info = session.get('user')
    if not user_info:
        return jsonify({'error': 'Não autenticado'}), 401

    user_id = user_info['user_id']
    data = request.get_json()
    upgrade_type = data.get('upgrade_type')
    cost = data.get('cost')

    if not game_manager:
        return jsonify({'error': 'Sistema de jogo não disponível'}), 503

    try:
        result = game_manager.buy_upgrade(user_id, upgrade_type, cost)
        return jsonify(result)
    except Exception as e:
        print(f"❌ Erro no upgrade: {e}")
        return jsonify({'error': str(e)}), 500

# ========== SYSTEM ROUTES ==========

@app.route('/healthz')
def health_check():
    """Health check para Render"""
    return 'OK'

@app.route('/api/system/health')
def system_health():
    """Health check completo do sistema"""
    db_status = "connected" if get_db_connection() else "disconnected"
    
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'database': db_status,
            'authentication': 'available' if auth_manager else 'unavailable',
            'game_system': 'available' if game_manager else 'unavailable'
        },
        'session': {
            'user_authenticated': bool(session.get('user')),
            'user_id': session.get('user_id')
        }
    })

@app.route('/debug/session')
def debug_session():
    """Debug da sessão"""
    session_info = {
        'session_exists': bool(session),
        'user_in_session': session.get('user'),
        'user_id_in_session': session.get('user_id'),
        'session_keys': list(session.keys()),
        'permanent': session.get('_permanent')
    }
    return jsonify(session_info)

@app.route('/debug/database')
def debug_database():
    """Debug do banco de dados"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM user_game_states")
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return jsonify({
                'status': 'connected',
                'user_game_states_count': count,
                'message': '✅ Conexão com PostgreSQL bem-sucedida!'
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': '❌ Não foi possível conectar ao banco'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'❌ Erro na conexão: {str(e)}'
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)