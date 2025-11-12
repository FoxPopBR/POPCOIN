import os
import psycopg2
import json
from psycopg2.extras import DictCursor
import urllib.parse
from psycopg2 import pool
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configurar logging
logger = logging.getLogger(__name__)

# ✅ CORREÇÃO: Pool de conexões simplificado
connection_pool = None
pool_lock = threading.Lock()

class DatabaseManager:
    """Gerenciador de banco de dados para o PopCoin IDLE - VERSÃO SIMPLIFICADA"""
    
    def __init__(self):
        self.initialized = False
        # ✅ CORREÇÃO: Usar DATABASE_URL do Render.com (já configurada nas variáveis de ambiente)
        self.database_url = os.environ.get('DATABASE_URL')
        self.init_db()
    
    def get_db_connection(self):
        """✅ CORREÇÃO: Obtém conexão SEM timeout (psycopg2 não suporta)"""
        global connection_pool
        
        try:
            if connection_pool:
                # ✅ CORREÇÃO: Removido timeout - não é suportado pelo psycopg2
                conn = connection_pool.getconn()
                if conn and not conn.closed:
                    return conn
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter conexão do pool: {e}")
        
        return self.create_direct_connection()

    def return_db_connection(self, conn):
        """✅ CORREÇÃO: Retorna conexão de forma segura"""
        global connection_pool
        try:
            if connection_pool and conn and not conn.closed:
                connection_pool.putconn(conn)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao retornar conexão: {e}")
            if conn:
                conn.close()

    def create_direct_connection(self):
        """✅ CORREÇÃO: Conexão direta otimizada"""
        if not self.database_url:
            logger.error("❌ DATABASE_URL não encontrada")
            return None

        try:
            # ✅ CORREÇÃO: Usar a DATABASE_URL do Render diretamente
            database_url = self.database_url
            
            # Converter postgres:// para postgresql:// se necessário
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')

            logger.info(f"🔗 Conectando ao banco: {database_url.split('@')[1] if '@' in database_url else 'Unknown'}")

            conn = psycopg2.connect(
                dsn=database_url,
                sslmode='require'  # Render requer SSL
            )

            # Testar conexão
            with conn.cursor() as cur:
                cur.execute("SELECT current_database();")
                result = cur.fetchone()
                db_name = result[0] if result else 'Unknown'
                
            logger.info(f"✅ Conectado ao banco: {db_name}")
            return conn

        except Exception as e:
            logger.error(f"❌ Erro na conexão com o banco: {e}")
            return None

    def init_db(self):
        """✅ CORREÇÃO: Inicialização simplificada"""
        global connection_pool
        
        if self.initialized:
            return
            
        logger.info("🔄 Iniciando inicialização do banco...")
        
        if not self.database_url:
            logger.error("❌ DATABASE_URL não encontrada - Modo desenvolvimento")
            self.initialized = True
            return
        
        try:
            # Testar conexão primeiro
            test_conn = self.create_direct_connection()
            if not test_conn:
                logger.error("❌ Não foi possível conectar ao banco")
                self.initialized = False
                return
                
            test_conn.close()
            
            # ✅ CORREÇÃO: Pool simplificado sem configurações complexas
            with pool_lock:
                database_url = self.database_url
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace('postgres://', 'postgresql://')
                    
                connection_pool = pool.SimpleConnectionPool(
                    1, 10,  # min=1, max=10 conexões
                    dsn=database_url
                )
                
            logger.info("✅ Pool de conexões criado!")
            
            # Criar tabelas
            self.create_tables()
            self.initialized = True
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização do banco: {e}")
            self.initialized = False

    def create_tables(self):
        """✅ CORREÇÃO: Tabelas com estrutura CORRIGIDA (sem conflito de colunas)"""
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para criar tabelas")
            return
        
        cur = conn.cursor()
        
        try:
            # ✅ CORREÇÃO: Primeiro verificar se as tabelas existem e quais colunas têm
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [row[0] for row in cur.fetchall()]
            
            # Tabela de usuários
            if 'users' not in existing_tables:
                cur.execute('''
                    CREATE TABLE users (
                        user_id VARCHAR(255) PRIMARY KEY,
                        email VARCHAR(255) NOT NULL,
                        display_name VARCHAR(255),
                        avatar_url TEXT,
                        email_verified BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        preferences JSONB DEFAULT '{}'::jsonb
                    )
                ''')
                logger.info("✅ Tabela 'users' criada")

            # Tabela de estados do jogo - ✅ CORREÇÃO: Usar 'coins' em vez de 'popcoins' para compatibilidade
            if 'user_game_states' not in existing_tables:
                cur.execute('''
                    CREATE TABLE user_game_states (
                        user_id VARCHAR(255) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                        coins BIGINT DEFAULT 0,
                        coins_per_click INTEGER DEFAULT 1,
                        coins_per_second NUMERIC(10,2) DEFAULT 0,
                        total_coins BIGINT DEFAULT 0,
                        prestige_level INTEGER DEFAULT 0,
                        click_count INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        experience INTEGER DEFAULT 0,
                        upgrades JSONB DEFAULT '{
                            "click_power": 1,
                            "auto_clicker": 0,
                            "auto_clickers": 0,
                            "click_bots": 0
                        }'::jsonb,
                        achievements JSONB DEFAULT '[]'::jsonb,
                        inventory JSONB DEFAULT '[]'::jsonb,
                        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                logger.info("✅ Tabela 'user_game_states' criada")
            else:
                # ✅ CORREÇÃO: Se a tabela já existe, verificar se tem a coluna 'coins'
                try:
                    cur.execute("SELECT coins FROM user_game_states LIMIT 1")
                    logger.info("✅ Coluna 'coins' já existe na tabela")
                except Exception:
                    # Se não tem a coluna 'coins', adicionar
                    logger.info("🔄 Adicionando coluna 'coins' à tabela existente...")
                    cur.execute('ALTER TABLE user_game_states ADD COLUMN coins BIGINT DEFAULT 0')
                    conn.commit()
                    logger.info("✅ Coluna 'coins' adicionada")

            # Tabela de conquistas
            if 'user_achievements' not in existing_tables:
                cur.execute('''
                    CREATE TABLE user_achievements (
                        achievement_id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
                        achievement_name VARCHAR(255) NOT NULL,
                        achievement_description TEXT,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, achievement_name)
                    )
                ''')
                logger.info("✅ Tabela 'user_achievements' criada")

            # Tabela de ranking
            if 'user_ranking' not in existing_tables:
                cur.execute('''
                    CREATE TABLE user_ranking (
                        user_id VARCHAR(255) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                        total_score BIGINT DEFAULT 0,
                        prestige_level INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                logger.info("✅ Tabela 'user_ranking' criada")

            # ✅ CORREÇÃO: Criar índices apenas se não existirem
            cur.execute('''
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'user_game_states' AND indexname = 'idx_user_game_states_coins'
            ''')
            if not cur.fetchone():
                cur.execute('CREATE INDEX idx_user_game_states_coins ON user_game_states(coins DESC)')

            cur.execute('''
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'user_ranking' AND indexname = 'idx_user_ranking_score'
            ''')
            if not cur.fetchone():
                cur.execute('CREATE INDEX idx_user_ranking_score ON user_ranking(total_score DESC)')

            cur.execute('''
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'users' AND indexname = 'idx_users_email'
            ''')
            if not cur.fetchone():
                cur.execute('CREATE INDEX idx_users_email ON users(email)')
            
            conn.commit()
            logger.info("✅ Todas as tabelas criadas/verificadas com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro na criação das tabelas: {e}")
            conn.rollback()
        finally:
            cur.close()
            self.return_db_connection(conn)

    # ========== MÉTODOS DE USUÁRIO ==========

    def save_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """✅ CORREÇÃO: Salva dados usando 'coins' em vez de 'popcoins'"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - modo desenvolvimento")
            return True
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para salvar dados do usuário")
            return False
        
        try:
            with conn.cursor() as cur:
                current_time = datetime.now()
                
                # Inserir/atualizar usuário
                cur.execute('''
                    INSERT INTO users (user_id, email, display_name, avatar_url, 
                                     email_verified, last_login, last_activity, preferences)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (user_id) DO UPDATE SET
                        email = EXCLUDED.email,
                        display_name = EXCLUDED.display_name,
                        avatar_url = EXCLUDED.avatar_url,
                        email_verified = EXCLUDED.email_verified,
                        last_login = EXCLUDED.last_login,
                        last_activity = EXCLUDED.last_activity,
                        preferences = EXCLUDED.preferences,
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    user_id,
                    user_data.get('email', ''),
                    user_data.get('name', ''),
                    user_data.get('picture'),
                    user_data.get('email_verified', False),
                    current_time,
                    current_time,
                    json.dumps(user_data.get('preferences', {}))
                ))
                
                # ✅ CORREÇÃO: Usar 'coins' em vez de 'popcoins' no banco
                if user_data.get('game_data'):
                    game_data = user_data['game_data']
                    # Converter 'popcoins' para 'coins' para o banco
                    coins_value = game_data.get('popcoins', game_data.get('coins', 0))
                    
                    cur.execute('''
                        INSERT INTO user_game_states 
                        (user_id, coins, coins_per_click, coins_per_second, 
                         total_coins, prestige_level, click_count, level, experience,
                         upgrades, achievements, inventory, last_update)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            coins = EXCLUDED.coins,
                            coins_per_click = EXCLUDED.coins_per_click,
                            coins_per_second = EXCLUDED.coins_per_second,
                            total_coins = EXCLUDED.total_coins,
                            prestige_level = EXCLUDED.prestige_level,
                            click_count = EXCLUDED.click_count,
                            level = EXCLUDED.level,
                            experience = EXCLUDED.experience,
                            upgrades = EXCLUDED.upgrades,
                            achievements = EXCLUDED.achievements,
                            inventory = EXCLUDED.inventory,
                            last_update = EXCLUDED.last_update,
                            updated_at = CURRENT_TIMESTAMP
                    ''', (
                        user_id,
                        coins_value,
                        game_data.get('coins_per_click', 1),
                        game_data.get('coins_per_second', 0),
                        game_data.get('total_coins', 0),
                        game_data.get('prestige_level', 0),
                        game_data.get('clicks', 0),
                        game_data.get('level', 1),
                        game_data.get('experience', 0),
                        json.dumps(game_data.get('upgrades', {})),
                        json.dumps(game_data.get('achievements', [])),
                        json.dumps(game_data.get('inventory', [])),
                        current_time
                    ))
                
                conn.commit()
                logger.info(f"✅ Dados salvos para usuário: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar dados do usuário {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            self.return_db_connection(conn)

    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """✅ CORREÇÃO: Converter 'coins' do banco para 'popcoins' na resposta"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - modo desenvolvimento")
            return None
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para obter dados do usuário")
            return None
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('''
                    SELECT 
                        u.user_id, u.email, u.display_name, u.avatar_url,
                        u.email_verified, u.created_at, u.last_login, u.last_activity, u.preferences,
                        g.coins, g.coins_per_click, g.coins_per_second, g.total_coins,
                        g.prestige_level, g.click_count, g.level, g.experience,
                        g.upgrades, g.achievements, g.inventory, g.last_update
                    FROM users u
                    LEFT JOIN user_game_states g ON u.user_id = g.user_id
                    WHERE u.user_id = %s
                ''', (user_id,))
                
                result = cur.fetchone()
                if not result:
                    logger.warning(f"⚠️ Usuário não encontrado: {user_id}")
                    return None
                
                # ✅ CORREÇÃO: Converter 'coins' do banco para 'popcoins' na resposta
                user_data = {
                    'uid': result['user_id'],
                    'email': result['email'],
                    'name': result['display_name'] or result['email'].split('@')[0],
                    'picture': result['avatar_url'] or '/static/images/default-avatar.png',
                    'email_verified': result['email_verified'],
                    'created_at': result['created_at'].isoformat() if result['created_at'] else datetime.now().isoformat(),
                    'last_login': result['last_login'].isoformat() if result['last_login'] else datetime.now().isoformat(),
                    'last_activity': result['last_activity'].isoformat() if result['last_activity'] else datetime.now().isoformat(),
                    'preferences': result['preferences'] or {},
                    'game_data': {
                        'popcoins': result['coins'] or 0,  # ✅ CORREÇÃO: coins → popcoins
                        'clicks': result['click_count'] or 0,
                        'level': result['level'] or 1,
                        'experience': result['experience'] or 0,
                        'coins_per_click': result['coins_per_click'] or 1,
                        'coins_per_second': float(result['coins_per_second'] or 0),
                        'total_coins': result['total_coins'] or 0,
                        'prestige_level': result['prestige_level'] or 0,
                        'upgrades': result['upgrades'] or {
                            'click_power': 1,
                            'auto_clicker': 0,
                            'auto_clickers': 0,
                            'click_bots': 0
                        },
                        'achievements': result['achievements'] or [],
                        'inventory': result['inventory'] or []
                    }
                }
                
                logger.info(f"✅ Dados carregados para usuário: {user_id}")
                return user_data
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter dados do usuário {user_id}: {e}")
            return None
        finally:
            self.return_db_connection(conn)

    # ========== MÉTODOS DO JOGO ==========

    def get_user_game_state(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Converter 'coins' para 'popcoins'"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - retornando estado padrão")
            return self.get_default_game_state()
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para obter estado do jogo")
            return self.get_default_game_state()
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('''
                    SELECT coins, coins_per_click, coins_per_second, total_coins,
                           prestige_level, click_count, level, experience, upgrades, achievements,
                           inventory, last_update
                    FROM user_game_states
                    WHERE user_id = %s
                ''', (user_id,))
                
                result = cur.fetchone()
                if result:
                    # ✅ CORREÇÃO: Converter 'coins' para 'popcoins'
                    game_state = {
                        'popcoins': result['coins'] or 0,
                        'coins_per_click': result['coins_per_click'] or 1,
                        'coins_per_second': float(result['coins_per_second'] or 0),
                        'total_coins': result['total_coins'] or 0,
                        'prestige_level': result['prestige_level'] or 0,
                        'clicks': result['click_count'] or 0,
                        'level': result['level'] or 1,
                        'experience': result['experience'] or 0,
                        'upgrades': result['upgrades'] or {
                            'click_power': 1,
                            'auto_clicker': 0,
                            'auto_clickers': 0,
                            'click_bots': 0
                        },
                        'achievements': result['achievements'] or [],
                        'inventory': result['inventory'] or [],
                        'last_update': result['last_update'].timestamp() if result['last_update'] else datetime.now().timestamp()
                    }
                    return game_state
                else:
                    return self.get_default_game_state()
                    
        except Exception as e:
            logger.error(f"❌ Erro ao obter estado do jogo para {user_id}: {e}")
            return self.get_default_game_state()
        finally:
            self.return_db_connection(conn)

    def save_game_state(self, user_id: str, game_state: Dict[str, Any]) -> bool:
        """✅ CORREÇÃO: Converter 'popcoins' para 'coins' no banco"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - modo desenvolvimento")
            return True
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para salvar estado do jogo")
            return False
        
        try:
            with conn.cursor() as cur:
                current_time = datetime.now()
                
                # ✅ CORREÇÃO: Converter 'popcoins' para 'coins' para o banco
                coins_value = game_state.get('popcoins', game_state.get('coins', 0))
                
                cur.execute('''
                    INSERT INTO user_game_states 
                    (user_id, coins, coins_per_click, coins_per_second, total_coins,
                     prestige_level, click_count, level, experience, upgrades, achievements, inventory, last_update)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        coins = EXCLUDED.coins,
                        coins_per_click = EXCLUDED.coins_per_click,
                        coins_per_second = EXCLUDED.coins_per_second,
                        total_coins = EXCLUDED.total_coins,
                        prestige_level = EXCLUDED.prestige_level,
                        click_count = EXCLUDED.click_count,
                        level = EXCLUDED.level,
                        experience = EXCLUDED.experience,
                        upgrades = EXCLUDED.upgrades,
                        achievements = EXCLUDED.achievements,
                        inventory = EXCLUDED.inventory,
                        last_update = EXCLUDED.last_update,
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    user_id,
                    coins_value,
                    game_state.get('coins_per_click', 1),
                    game_state.get('coins_per_second', 0),
                    game_state.get('total_coins', 0),
                    game_state.get('prestige_level', 0),
                    game_state.get('clicks', 0),
                    game_state.get('level', 1),
                    game_state.get('experience', 0),
                    json.dumps(game_state.get('upgrades', {})),
                    json.dumps(game_state.get('achievements', [])),
                    json.dumps(game_state.get('inventory', [])),
                    current_time
                ))
                
                # Atualizar ranking
                cur.execute('''
                    INSERT INTO user_ranking (user_id, total_score, prestige_level, level)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        total_score = EXCLUDED.total_score,
                        prestige_level = EXCLUDED.prestige_level,
                        level = EXCLUDED.level,
                        last_updated = CURRENT_TIMESTAMP
                ''', (user_id, game_state.get('total_coins', 0), 
                      game_state.get('prestige_level', 0), game_state.get('level', 1)))
                
                conn.commit()
                logger.info(f"✅ Estado do jogo salvo para: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado do jogo para {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            self.return_db_connection(conn)

    def get_default_game_state(self) -> Dict[str, Any]:
        """Estado padrão do jogo"""
        return {
            'popcoins': 0,
            'coins_per_click': 1,
            'coins_per_second': 0,
            'total_coins': 0,
            'prestige_level': 0,
            'clicks': 0,
            'level': 1,
            'experience': 0,
            'upgrades': {
                'click_power': 1,
                'auto_clicker': 0,
                'auto_clickers': 0,
                'click_bots': 0
            },
            'achievements': [],
            'inventory': [],
            'last_update': datetime.now().timestamp()
        }

    # ... (manter os outros métodos get_ranking, health_check, etc.)

# ✅ CORREÇÃO: Instância única
db_manager = None

def get_database_manager():
    """Singleton para DatabaseManager"""
    global db_manager
    if db_manager is None:
        try:
            db_manager = DatabaseManager()
            if db_manager.initialized:
                logger.info("✅ DatabaseManager inicializado com sucesso!")
            else:
                logger.error("❌ DatabaseManager falhou na inicialização")
        except Exception as e:
            logger.error(f"❌ Falha crítica ao criar DatabaseManager: {e}")
            db_manager = None
    return db_manager

# Inicialização controlada
logger.info("📦 Inicializando db_models.py...")
db_manager = get_database_manager()