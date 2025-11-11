import os
import psycopg2
from psycopg2 import sql

def get_db_connection():
    """Obtém conexão com o banco de dados"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render.com usa PostgreSQL
        conn = psycopg2.connect(database_url, sslmode='require')
    else:
        # Desenvolvimento local
        conn = psycopg2.connect(
            host='localhost',
            database='popcoin_db',
            user='postgres',
            password='password'
        )
    return conn

def init_db():
    """Inicializa o banco de dados com tabelas necessárias"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Tabela de estados do jogo
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_game_states (
            user_id VARCHAR(255) PRIMARY KEY,
            game_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de usuários (para informações adicionais)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            display_name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

# Inicializar o banco de dados quando o módulo for carregado
init_db()