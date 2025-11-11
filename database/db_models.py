# database/db_models.py - VERSÃO COM POOL
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse
from psycopg2 import pool
import threading

# Pool de conexões thread-safe
connection_pool = None
pool_lock = threading.Lock()

def get_db_connection():
    """Obtém conexão do pool ou cria conexão direta"""
    global connection_pool
    
    try:
        # Tentar usar o pool primeiro
        if connection_pool:
            conn = connection_pool.getconn()
            if conn and not conn.closed:
                return conn
    except Exception as e:
        print(f"⚠️ Erro ao obter conexão do pool: {e}")
    
    # Fallback: conexão direta
    return create_direct_connection()

def return_db_connection(conn):
    """Retorna conexão ao pool"""
    global connection_pool
    try:
        if connection_pool and conn and not conn.closed:
            connection_pool.putconn(conn)
    except Exception as e:
        print(f"⚠️ Erro ao retornar conexão: {e}")
        if conn:
            conn.close()

def create_direct_connection():
    """Cria conexão direta com PostgreSQL"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return None
    
    try:
        # Parse da URL para debugging seguro
        parsed_url = urllib.parse.urlparse(database_url)
        safe_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
        print(f"🔗 Conexão direta à: {safe_url}")
        
        # Converter URL se necessário
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://')
        
        # Opções de conexão para SSL
        connect_args = {
            'dsn': database_url,
            'sslmode': 'require'
        }
        
        conn = psycopg2.connect(**connect_args)
        
        # Testar a conexão
        cur = conn.cursor()
        cur.execute("SELECT 1 as test;")
        result = cur.fetchone()
        cur.close()
        
        if result and result[0] == 1:
            print("✅ Conexão direta PostgreSQL validada!")
            return conn
        else:
            print("❌ Teste de conexão direta falhou")
            conn.close()
            return None
            
    except Exception as e:
        print(f"❌ Erro na conexão direta: {e}")
        return None

def init_db():
    """Inicializa o banco de dados e pool de conexões"""
    global connection_pool
    
    print("🔄 Iniciando inicialização do banco...")
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return
    
    try:
        # Criar pool de conexões
        with pool_lock:
            connection_pool = pool.SimpleConnectionPool(
                1,  # min connections
                5,  # max connections (reduzido para Render)
                dsn=database_url,
                sslmode='require'
            )
        print("✅ Pool de conexões PostgreSQL criado!")
        
        # Criar tabelas
        create_tables()
        
    except Exception as e:
        print(f"❌ Erro na criação do pool: {e}")
        # Continuar com conexões diretas

def create_tables():
    """Cria tabelas necessárias"""
    conn = get_db_connection()
    if not conn:
        print("❌ Falha ao conectar para criar tabelas")
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
        print("✅ Tabela user_game_states criada/verificada!")
        
    except Exception as e:
        print(f"❌ Erro na criação da tabela: {e}")
        conn.rollback()
    finally:
        cur.close()
        return_db_connection(conn)

# Inicializar o banco quando o módulo for carregado
print("📦 Carregando db_models.py...")
init_db()