from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import os
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-popcoin-segura-aqui')
app.permanent_session_lifetime = timedelta(days=7)

# Configurações do Firebase
FIREBASE_CONFIG = {
    "apiKey": os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY'),
    "authDomain": os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN'),
    "projectId": os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID'),
    "storageBucket": os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET'),
    "messagingSenderId": os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID'),
    "appId": os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID')
}

# Importar módulos com fallback
try:
    from auth.auth_manager import AuthManager
    auth_manager = AuthManager()
except ImportError as e:
    print(f"AuthManager não disponível: {e}")
    auth_manager = None

try:
    from game.game_logic import GameManager
    game_manager = GameManager()
except ImportError as e:
    print(f"GameManager não disponível: {e}")
    game_manager = None

# Rotas principais
@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html', firebase_config=FIREBASE_CONFIG)

@app.route('/game')
def game():
    """Página principal do jogo"""
    if not session.get('user_authenticated'):
        return redirect(url_for('index'))
    return render_template('game.html')

# API Routes
@app.route('/api/game/state')
def get_game_state():
    """Obter estado atual do jogo"""
    if not game_manager:
        return jsonify({"coins": 0, "coins_per_click": 1, "coins_per_second": 0})
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        game_state = game_manager.get_user_game_state(user_id)
        return jsonify(game_state)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/game/action', methods=['POST'])
def game_action():
    """Executar ação no jogo"""
    if not game_manager:
        return jsonify({"error": "Sistema de jogo não disponível"}), 503
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        action_data = request.json
        result = game_manager.process_action(user_id, action_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Auth Routes
@app.route('/api/auth/status')
def auth_status():
    """Verificar status de autenticação"""
    return jsonify({
        "authenticated": session.get('user_authenticated', False),
        "user": session.get('user_info')
    })

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Processar login"""
    if not auth_manager:
        return jsonify({"error": "Sistema de autenticação não disponível"}), 503
    
    token = request.json.get('token')
    user_info = auth_manager.verify_firebase_token(token)
    
    if user_info:
        session.permanent = True
        session['user_authenticated'] = True
        session['user_id'] = user_info['uid']
        session['user_info'] = user_info
        return jsonify({"success": True, "user": user_info})
    else:
        return jsonify({"error": "Token inválido"}), 401

@app.route('/api/auth/logout')
def auth_logout():
    """Fazer logout"""
    session.clear()
    return jsonify({"success": True})

# Health check para Render
@app.route('/healthz')
def health_check():
    return jsonify({"status": "healthy", "python": "3.10.11"})

# Rota de informações do sistema
@app.route('/api/system/info')
def system_info():
    return jsonify({
        "status": "online",
        "python_version": "3.10.11",
        "game_system": "available" if game_manager else "unavailable",
        "auth_system": "available" if auth_manager else "unavailable"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', False))