from flask import Flask, render_template, jsonify, request, session, redirect, url_for
import os
import time
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-popcoin-segura-aqui-32-chars')
app.permanent_session_lifetime = timedelta(days=7)

# Configurações do Firebase - COM VALORES PADRÃO
FIREBASE_CONFIG = {
    "apiKey": os.environ.get('NEXT_PUBLIC_FIREBASE_API_KEY', 'AIzaSyC_O0ur0PaP8iB_t2i6_m0WLU9C5FM4PZ4'),
    "authDomain": os.environ.get('NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN', 'popcoin-idle-829ae.firebaseapp.com'),
    "projectId": os.environ.get('NEXT_PUBLIC_FIREBASE_PROJECT_ID', 'popcoin-idle-829ae'),
    "storageBucket": os.environ.get('NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET', 'popcoin-idle-829ae.firebasestorage.app'),
    "messagingSenderId": os.environ.get('NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID', '337350823197'),
    "appId": os.environ.get('NEXT_PUBLIC_FIREBASE_APP_ID', '1:337350823197:web:4928ae4827e21c585da5f4')
}

# Conexão com PostgreSQL do Render
def get_db_connection():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        try:
            # Converter para formato psycopg2
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return None
    print("❌ DATABASE_URL não encontrada")
    return None

# Inicializar banco de dados
def init_db():
    conn = get_db_connection()
    if not conn:
        print("❌ No database connection available")
        return
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_game_states (
                user_id VARCHAR(255) PRIMARY KEY,
                game_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("✅ PostgreSQL inicializado com sucesso!")
    except Exception as e:
        print(f"❌ Erro na inicialização do PostgreSQL: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# Importar módulos com fallback melhorado
try:
    from auth.auth_manager import AuthManager
    auth_manager = AuthManager()
    print("✅ AuthManager carregado")
except ImportError as e:
    print(f"⚠️ AuthManager não disponível: {e}")
    auth_manager = None

try:
    from game.game_logic import GameManager
    game_manager = GameManager()
    print("✅ GameManager carregado")
except ImportError as e:
    print(f"⚠️ GameManager não disponível: {e}")
    game_manager = None

# Inicializar banco na startup
init_db()

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
    return render_template('game.html', firebase_config=FIREBASE_CONFIG)

# API Routes
@app.route('/api/game/state', methods=['GET', 'POST'])
def get_game_state():
    """Obter ou salvar estado atual do jogo"""
    if not game_manager:
        return jsonify({"coins": 0, "coins_per_click": 1, "coins_per_second": 0})
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    
    try:
        if request.method == 'GET':
            game_state = game_manager.get_user_game_state(user_id)
            return jsonify(game_state)
        elif request.method == 'POST':
            # Salvar estado do jogo recebido do frontend
            game_data = request.json
            game_manager.save_game_state(user_id, game_data)
            return jsonify({"success": True})
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

# Auth Routes - CORRIGIDAS
@app.route('/api/auth/status')
def auth_status():
    """Verificar status de autenticação de forma mais robusta"""
    try:
        user_authenticated = session.get('user_authenticated', False)
        user_info = session.get('user_info')
        
        # Se não está autenticado na sessão, limpar qualquer dado residual
        if not user_authenticated:
            session.pop('user_id', None)
            session.pop('user_info', None)
            return jsonify({
                "authenticated": False,
                "user": None
            })
        
        return jsonify({
            "authenticated": True,
            "user": user_info
        })
    except Exception as e:
        print(f"❌ Erro em auth_status: {e}")
        return jsonify({"authenticated": False, "user": None})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Processar login com tratamento melhorado"""
    if not auth_manager:
        return jsonify({"error": "Sistema de autenticação não disponível"}), 503
    
    try:
        token = request.json.get('token')
        if not token:
            return jsonify({"error": "Token não fornecido"}), 400
        
        user_info = auth_manager.verify_firebase_token(token)
        
        if user_info:
            # Configurar sessão
            session.permanent = True
            session['user_authenticated'] = True
            session['user_id'] = user_info['uid']
            session['user_info'] = user_info
            
            print(f"✅ Login bem-sucedido para: {user_info['email']}")
            return jsonify({
                "success": True, 
                "user": user_info,
                "message": "Login realizado com sucesso"
            })
        else:
            # Limpar sessão em caso de token inválido
            session.clear()
            return jsonify({"error": "Token inválido ou expirado"}), 401
            
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        session.clear()
        return jsonify({"error": "Erro interno no servidor"}), 500

@app.route('/api/auth/logout')
def auth_logout():
    """Fazer logout completo"""
    try:
        session.clear()
        return jsonify({"success": True, "message": "Logout realizado"})
    except Exception as e:
        print(f"❌ Erro no logout: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

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

@app.route('/api/system/health')
def system_health():
    """Health check completo do sistema"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "session": {
            "user_authenticated": session.get('user_authenticated', False),
            "user_id": session.get('user_id'),
            "has_user_info": bool(session.get('user_info'))
        },
        "services": {
            "database": "connected" if get_db_connection() else "disconnected",
            "firebase": "initialized",
            "game_system": "available" if game_manager else "unavailable"
        }
    })

# Rota de debug para banco de dados
@app.route('/debug/database')
def debug_database():
    """Rota para debug do banco de dados"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            cur.close()
            conn.close()
            return jsonify({
                "status": "connected",
                "database_version": db_version[0] if db_version else "unknown",
                "message": "✅ Conexão com PostgreSQL bem-sucedida!"
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "❌ Não foi possível conectar ao banco"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ Erro na conexão: {str(e)}"
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_DEBUG', False))