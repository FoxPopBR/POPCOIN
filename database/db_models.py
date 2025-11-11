import os
import psycopg2
from psycopg2 import sql

def get_db_connection():
    """Obtém conexão com o banco de dados com fallback para SQLite"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Render.com usa PostgreSQL
        try:
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}")
            print("Falling back to SQLite...")
    
    # Fallback para SQLite (desenvolvimento)
    try:
        import sqlite3
        conn = sqlite3.connect('popcoin.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"SQLite connection also failed: {e}")
        return None

def init_db():
    """Inicializa o banco de dados com fallback"""
    conn = get_db_connection()
    if not conn:
        print("No database connection available")
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
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# Inicializar o banco de dados quando o módulo for carregado
init_db()