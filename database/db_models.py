import os
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

def get_db_connection():
    """Obtém conexão com o PostgreSQL do Render - COM SSL FORÇADO"""
    database_url = os.environ.get('DATABASE_URL')
    
    print(f"🔍 DATABASE_URL presente: {bool(database_url)}")
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        return None
    
    try:
        # Parse da URL para debugging seguro
        parsed_url = urllib.parse.urlparse(database_url)
        safe_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
        print(f"🔗 Conectando à: {safe_url}")
        
        # Converter URL se necessário
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://')
            print("🔄 URL convertida de postgres:// para postgresql://")
        
        # Opções de conexão para SSL
        connect_args = {
            'dsn': database_url,
            'sslmode': 'require'
        }
        
        print("🔐 Tentando conexão com SSL...")
        conn = psycopg2.connect(**connect_args)
        
        # Testar a conexão
        cur = conn.cursor()
        cur.execute("SELECT 1 as test;")
        result = cur.fetchone()
        cur.close()
        
        if result and result[0] == 1:
            print("✅ Conexão PostgreSQL testada e validada!")
            return conn
        else:
            print("❌ Teste de conexão falhou")
            conn.close()
            return None
            
    except psycopg2.OperationalError as e:
        print(f"❌ Erro operacional PostgreSQL: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado: {type(e).__name__}: {e}")
        return None

def init_db():
    """Inicializa o banco de dados"""
    print("🔄 Iniciando inicialização do banco...")
    conn = get_db_connection()
    if not conn:
        print("❌ Falha na conexão durante init_db")
        return
    
    cur = conn.cursor()
    
    try:
        # Tabela de estados do jogo
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_game_states (
                user_id VARCHAR(255) PRIMARY KEY,
                game_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("✅ Tabela user_game_states criada/verificada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro na criação da tabela: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
        print("🔒 Conexão fechada após init_db")

# Inicializar o banco de dados quando o módulo for carregado
print("📦 Carregando db_models.py...")
init_db()