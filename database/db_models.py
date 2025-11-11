import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Obtém conexão com o PostgreSQL do Render"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith('postgres://'):
        # Render usa PostgreSQL
        try:
            # Converter para formato psycopg2
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return None
    
    print("❌ DATABASE_URL não encontrada ou inválida")
    return None

def init_db():
    """Inicializa o banco de dados"""
    conn = get_db_connection()
    if not conn:
        print("❌ No database connection available")
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
        print("✅ PostgreSQL Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# Inicializar o banco de dados quando o módulo for carregado
init_db()