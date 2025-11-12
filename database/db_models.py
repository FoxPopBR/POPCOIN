# database/db_models.py - VERSÃO CORRIGIDA E INTEGRADA
import os
import psycopg2
import json
from psycopg2.extras import RealDictCursor, DictCursor
import urllib.parse
from psycopg2 import pool
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configurar logging
logger = logging.getLogger(__name__)

# Pool de conexões thread-safe
connection_pool = None
pool_lock = threading.Lock()

class DatabaseManager:
    """Gerenciador de banco de dados para o PopCoin IDLE"""
    
    def __init__(self):
        self.initialized = False
        self.init_db()
    
    def get_db_connection(self):
        """Obtém conexão do pool ou cria conexão direta"""
        global connection_pool
        
        try:
            # Tentar usar o pool primeiro
            if connection_pool:
                conn = connection_pool.getconn()
                if conn and not conn.closed:
                    return conn
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter conexão do pool: {e}")
        
        # Fallback: conexão direta
        return self.create_direct_connection()

    def return_db_connection(self, conn):
        """Retorna conexão ao pool"""
        global connection_pool
        try:
            if connection_pool and conn and not conn.closed:
                connection_pool.putconn(conn)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao retornar conexão: {e}")
            if conn:
                conn.close()

    def create_direct_connection(self):
        """Cria conexão direta com PostgreSQL"""
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.error("❌ DATABASE_URL não encontrada")
            return None
        
        try:
            # Parse da URL para debugging seguro
            parsed_url = urllib.parse.urlparse(database_url)
            safe_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
            logger.info(f"🔗 Conexão direta à: {safe_url}")
            
            # Converter URL se necessário (Render.com usa postgres://)
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            
            # Conexão com timeout
            conn = psycopg2.connect(
                dsn=database_url,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            
            # Testar a conexão
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as test;")
                result = cur.fetchone()
            
            if result and result[0] == 1:
                logger.info("✅ Conexão direta PostgreSQL validada!")
                return conn
            else:
                logger.error("❌ Teste de conexão direta falhou")
                conn.close()
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro na conexão direta: {e}")
            return None

    def init_db(self):
        """Inicializa o banco de dados e pool de conexões"""
        global connection_pool
        
        logger.info("🔄 Iniciando inicialização do banco...")
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            logger.error("❌ DATABASE_URL não encontrada - Modo desenvolvimento sem banco")
            self.initialized = False
            return
        
        try:
            # Criar pool de conexões
            with pool_lock:
                connection_pool = pool.SimpleConnectionPool(
                    1,  # min connections
                    10, # max connections
                    dsn=database_url,
                    connect_timeout=10,
                    keepalives=1,
                    keepalives_idle=30
                )
            logger.info("✅ Pool de conexões PostgreSQL criado!")
            
            # Criar tabelas
            self.create_tables()
            self.initialized = True
            
        except Exception as e:
            logger.error(f"❌ Erro na criação do pool: {e}")
            # Continuar com conexões diretas
            self.initialized = True

    def create_tables(self):
        """Cria tabelas necessárias para o PopCoin IDLE"""
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para criar tabelas")
            return
        
        cur = conn.cursor()
        
        try:
            # Tabela de usuários (dados do perfil)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(255) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255),
                    avatar_url TEXT,
                    email_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    preferences JSONB DEFAULT '{}'::jsonb
                )
            ''')
            
            # Tabela de estados do jogo
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_game_states (
                    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                    coins BIGINT DEFAULT 0,
                    coins_per_click INTEGER DEFAULT 1,
                    coins_per_second NUMERIC(10,2) DEFAULT 0,
                    total_coins BIGINT DEFAULT 0,
                    prestige_level INTEGER DEFAULT 0,
                    click_count INTEGER DEFAULT 0,
                    upgrades JSONB DEFAULT '{
                        "click_power": 1,
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
            
            # Tabela de conquistas do usuário
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    achievement_id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
                    achievement_name VARCHAR(255) NOT NULL,
                    achievement_description TEXT,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, achievement_name)
                )
            ''')
            
            # Tabela de ranking (para estatísticas)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_ranking (
                    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                    total_score BIGINT DEFAULT 0,
                    prestige_level INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Índices para performance
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_game_states_coins 
                ON user_game_states(coins DESC)
            ''')
            
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_ranking_score 
                ON user_ranking(total_score DESC)
            ''')
            
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON users(email)
            ''')
            
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
        """Salva dados completos do usuário (perfil + jogo)"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - modo desenvolvimento")
            return True
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para salvar dados do usuário")
            return False
        
        try:
            with conn.cursor() as cur:
                # Inserir/atualizar usuário
                cur.execute('''
                    INSERT INTO users (user_id, email, display_name, avatar_url, 
                                     email_verified, last_login, preferences)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (user_id) DO UPDATE SET
                        email = EXCLUDED.email,
                        display_name = EXCLUDED.display_name,
                        avatar_url = EXCLUDED.avatar_url,
                        email_verified = EXCLUDED.email_verified,
                        last_login = EXCLUDED.last_login,
                        preferences = EXCLUDED.preferences,
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    user_id,
                    user_data.get('email', ''),
                    user_data.get('name', ''),
                    user_data.get('picture'),
                    user_data.get('email_verified', False),
                    datetime.now(),
                    json.dumps(user_data.get('preferences', {}))
                ))
                
                # Inserir/atualizar estado do jogo se existir game_data
                if user_data.get('game_data'):
                    game_data = user_data['game_data']
                    cur.execute('''
                        INSERT INTO user_game_states 
                        (user_id, coins, coins_per_click, coins_per_second, 
                         total_coins, prestige_level, click_count, upgrades, 
                         achievements, inventory, last_update)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            coins = EXCLUDED.coins,
                            coins_per_click = EXCLUDED.coins_per_click,
                            coins_per_second = EXCLUDED.coins_per_second,
                            total_coins = EXCLUDED.total_coins,
                            prestige_level = EXCLUDED.prestige_level,
                            click_count = EXCLUDED.click_count,
                            upgrades = EXCLUDED.upgrades,
                            achievements = EXCLUDED.achievements,
                            inventory = EXCLUDED.inventory,
                            last_update = EXCLUDED.last_update,
                            updated_at = CURRENT_TIMESTAMP
                    ''', (
                        user_id,
                        game_data.get('popcoins', 0),
                        game_data.get('coins_per_click', 1),
                        game_data.get('coins_per_second', 0),
                        game_data.get('total_coins', 0),
                        game_data.get('prestige_level', 0),
                        game_data.get('clicks', 0),
                        json.dumps(game_data.get('upgrades', {})),
                        json.dumps(game_data.get('achievements', [])),
                        json.dumps(game_data.get('inventory', [])),
                        datetime.now()
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
        """Obtém dados completos do usuário"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - modo desenvolvimento")
            return None
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para obter dados do usuário")
            return None
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Buscar dados do usuário e jogo
                cur.execute('''
                    SELECT 
                        u.user_id, u.email, u.display_name, u.avatar_url,
                        u.email_verified, u.created_at, u.last_login, u.preferences,
                        g.coins, g.coins_per_click, g.coins_per_second, g.total_coins,
                        g.prestige_level, g.click_count, g.upgrades, g.achievements,
                        g.inventory, g.last_update
                    FROM users u
                    LEFT JOIN user_game_states g ON u.user_id = g.user_id
                    WHERE u.user_id = %s
                ''', (user_id,))
                
                result = cur.fetchone()
                if not result:
                    logger.warning(f"⚠️ Usuário não encontrado: {user_id}")
                    return None
                
                # Construir estrutura compatível com o app.py
                user_data = {
                    'uid': result['user_id'],
                    'email': result['email'],
                    'name': result['display_name'] or result['email'].split('@')[0],
                    'picture': result['avatar_url'],
                    'email_verified': result['email_verified'],
                    'created_at': result['created_at'].isoformat() if result['created_at'] else datetime.now().isoformat(),
                    'last_login': result['last_login'].isoformat() if result['last_login'] else datetime.now().isoformat(),
                    'preferences': result['preferences'] or {},
                    'game_data': {
                        'popcoins': result['coins'] or 0,
                        'clicks': result['click_count'] or 0,
                        'level': 1,  # Campo mantido para compatibilidade
                        'experience': 0,  # Campo mantido para compatibilidade
                        'coins_per_click': result['coins_per_click'] or 1,
                        'coins_per_second': float(result['coins_per_second'] or 0),
                        'total_coins': result['total_coins'] or 0,
                        'prestige_level': result['prestige_level'] or 0,
                        'upgrades': result['upgrades'] or {
                            'click_power': 1,
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
        """Obtém estado do jogo para um usuário"""
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
                           prestige_level, click_count, upgrades, achievements,
                           inventory, last_update
                    FROM user_game_states
                    WHERE user_id = %s
                ''', (user_id,))
                
                result = cur.fetchone()
                if result:
                    game_state = {
                        'coins': result['coins'] or 0,
                        'coins_per_click': result['coins_per_click'] or 1,
                        'coins_per_second': float(result['coins_per_second'] or 0),
                        'total_coins': result['total_coins'] or 0,
                        'prestige_level': result['prestige_level'] or 0,
                        'click_count': result['click_count'] or 0,
                        'upgrades': result['upgrades'] or {
                            'click_power': 1,
                            'auto_clickers': 0,
                            'click_bots': 0
                        },
                        'achievements': result['achievements'] or [],
                        'inventory': result['inventory'] or [],
                        'last_update': result['last_update'].timestamp() if result['last_update'] else datetime.now().timestamp()
                    }
                    return game_state
                else:
                    # Retornar estado padrão se não existir
                    return self.get_default_game_state()
                    
        except Exception as e:
            logger.error(f"❌ Erro ao obter estado do jogo para {user_id}: {e}")
            return self.get_default_game_state()
        finally:
            self.return_db_connection(conn)

    def save_game_state(self, user_id: str, game_state: Dict[str, Any]) -> bool:
        """Salva estado do jogo para um usuário"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - modo desenvolvimento")
            return True
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para salvar estado do jogo")
            return False
        
        try:
            with conn.cursor() as cur:
                # Verificar se o usuário existe
                cur.execute('SELECT 1 FROM users WHERE user_id = %s', (user_id,))
                if not cur.fetchone():
                    logger.warning(f"⚠️ Usuário {user_id} não existe, criando...")
                    # Criar entrada básica do usuário
                    cur.execute('''
                        INSERT INTO users (user_id, email, display_name)
                        VALUES (%s, %s, %s)
                    ''', (user_id, f"{user_id}@temp.com", "Jogador"))
                
                # Inserir/atualizar estado do jogo
                cur.execute('''
                    INSERT INTO user_game_states 
                    (user_id, coins, coins_per_click, coins_per_second, total_coins,
                     prestige_level, click_count, upgrades, achievements, inventory, last_update)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        coins = EXCLUDED.coins,
                        coins_per_click = EXCLUDED.coins_per_click,
                        coins_per_second = EXCLUDED.coins_per_second,
                        total_coins = EXCLUDED.total_coins,
                        prestige_level = EXCLUDED.prestige_level,
                        click_count = EXCLUDED.click_count,
                        upgrades = EXCLUDED.upgrades,
                        achievements = EXCLUDED.achievements,
                        inventory = EXCLUDED.inventory,
                        last_update = EXCLUDED.last_update,
                        updated_at = CURRENT_TIMESTAMP
                ''', (
                    user_id,
                    game_state.get('coins', 0),
                    game_state.get('coins_per_click', 1),
                    game_state.get('coins_per_second', 0),
                    game_state.get('total_coins', 0),
                    game_state.get('prestige_level', 0),
                    game_state.get('click_count', 0),
                    json.dumps(game_state.get('upgrades', {})),
                    json.dumps(game_state.get('achievements', [])),
                    json.dumps(game_state.get('inventory', [])),
                    datetime.now()
                ))
                
                # Atualizar ranking
                cur.execute('''
                    INSERT INTO user_ranking (user_id, total_score, prestige_level)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        total_score = EXCLUDED.total_score,
                        prestige_level = EXCLUDED.prestige_level,
                        last_updated = CURRENT_TIMESTAMP
                ''', (user_id, game_state.get('total_coins', 0), game_state.get('prestige_level', 0)))
                
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
        """Retorna estado padrão do jogo"""
        return {
            'coins': 0,
            'coins_per_click': 1,
            'coins_per_second': 0,
            'total_coins': 0,
            'prestige_level': 0,
            'upgrades': {
                'click_power': 1,
                'auto_clickers': 0,
                'click_bots': 0
            },
            'click_count': 0,
            'achievements': [],
            'inventory': [],
            'last_update': datetime.now().timestamp()
        }

    # ========== MÉTODOS DE RANKING ==========

    def get_ranking(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém ranking de jogadores"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - retornando ranking mock")
            return self.get_mock_ranking()
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para obter ranking")
            return self.get_mock_ranking()
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('''
                    SELECT u.user_id, u.display_name, r.total_score as popcoins, 
                           r.prestige_level as level
                    FROM user_ranking r
                    JOIN users u ON r.user_id = u.user_id
                    ORDER BY r.total_score DESC, r.prestige_level DESC
                    LIMIT %s
                ''', (limit,))
                
                results = cur.fetchall()
                ranking = []
                
                for row in results:
                    ranking.append({
                        'uid': row['user_id'],
                        'name': row['display_name'] or 'Jogador',
                        'popcoins': row['popcoins'] or 0,
                        'level': row['level'] or 0
                    })
                
                logger.info(f"✅ Ranking carregado: {len(ranking)} jogadores")
                return ranking
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter ranking: {e}")
            return self.get_mock_ranking()
        finally:
            self.return_db_connection(conn)

    def get_mock_ranking(self) -> List[Dict[str, Any]]:
        """Retorna ranking mock para desenvolvimento"""
        return [
            {'uid': 'user_1', 'name': 'Jogador Top', 'popcoins': 15000, 'level': 15},
            {'uid': 'user_2', 'name': 'Clique Mestre', 'popcoins': 12000, 'level': 12},
            {'uid': 'user_3', 'name': 'Coletor Ávido', 'popcoins': 8000, 'level': 10}
        ]

    # ========== MÉTODOS DE MANUTENÇÃO ==========

    def health_check(self) -> bool:
        """Verifica a saúde do banco de dados"""
        if not self.initialized:
            return False
        
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as health_check")
                result = cur.fetchone()
                return result and result[0] == 1
        except Exception as e:
            logger.error(f"❌ Health check falhou: {e}")
            return False
        finally:
            self.return_db_connection(conn)

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Limpa sessões antigas (para manutenção)"""
        if not self.initialized:
            return 0
        
        conn = self.get_db_connection()
        if not conn:
            return 0
        
        try:
            with conn.cursor() as cur:
                cur.execute('''
                    DELETE FROM user_game_states 
                    WHERE last_update < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND user_id IN (
                        SELECT user_id FROM users 
                        WHERE last_login < CURRENT_TIMESTAMP - INTERVAL '%s days'
                    )
                ''', (days, days))
                
                deleted_rows = cur.rowcount
                conn.commit()
                
                logger.info(f"🧹 Limpeza concluída: {deleted_rows} registros removidos")
                return deleted_rows
                
        except Exception as e:
            logger.error(f"❌ Erro na limpeza: {e}")
            conn.rollback()
            return 0
        finally:
            self.return_db_connection(conn)

# Instância global do DatabaseManager
db_manager = None

def init_database_manager():
    """Inicializa o gerenciador de banco de dados global"""
    global db_manager
    try:
        db_manager = DatabaseManager()
        logger.info("✅ DatabaseManager inicializado com sucesso!")
        return db_manager
    except Exception as e:
        logger.error(f"❌ Falha ao inicializar DatabaseManager: {e}")
        return None

# Inicializar quando o módulo for carregado
logger.info("📦 Inicializando db_models.py...")
db_manager = init_database_manager()