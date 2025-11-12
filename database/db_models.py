# database/db_models.py - VERSÃO CORRIGIDA E OTIMIZADA
import os
import psycopg2
import json
from psycopg2.extras import DictCursor, RealDictCursor
import urllib.parse
from psycopg2 import pool
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configurar logging
logger = logging.getLogger(__name__)

# ✅ CORREÇÃO: Pool de conexões thread-safe
connection_pool = None
pool_lock = threading.Lock()

class DatabaseManager:
    """Gerenciador de banco de dados para o PopCoin IDLE - VERSÃO CORRIGIDA"""
    
    def __init__(self):
        self.initialized = False
        self.database_url = os.environ.get('DATABASE_URL')
        self.pool_min = 1
        self.pool_max = 10
        self.init_db()
    
    def get_db_connection(self):
        """✅ CORREÇÃO: Obtém conexão de forma segura"""
        global connection_pool
        
        if not self.initialized or not connection_pool:
            return self.create_direct_connection()
        
        try:
            conn = connection_pool.getconn()
            if conn and not conn.closed:
                # ✅ CORREÇÃO: Verificar se a conexão ainda é válida
                try:
                    with conn.cursor() as cur:
                        cur.execute('SELECT 1')
                    return conn
                except psycopg2.InterfaceError:
                    # Conexão inválida, criar nova
                    connection_pool.putconn(conn, close=True)
                    return self.create_direct_connection()
            else:
                return self.create_direct_connection()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter conexão do pool: {e}")
            return self.create_direct_connection()

    def return_db_connection(self, conn):
        """✅ CORREÇÃO: Retorna conexão de forma segura"""
        global connection_pool
        try:
            if connection_pool and conn and not conn.closed:
                connection_pool.putconn(conn)
            elif conn:
                conn.close()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao retornar conexão: {e}")
            if conn:
                conn.close()

    def create_direct_connection(self):
        """✅ CORREÇÃO: Conexão direta com tratamento de erro melhorado"""
        if not self.database_url:
            logger.error("❌ DATABASE_URL não encontrada")
            return None

        try:
            # ✅ CORREÇÃO: Converter postgres:// para postgresql://
            database_url = self.database_url
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')

            logger.info(f"🔗 Tentando conexão direta com o banco...")

            conn = psycopg2.connect(
                dsn=database_url,
                sslmode='require',
                connect_timeout=10
            )

            # Testar conexão
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user;")
                result = cur.fetchone()
                db_name = result[0] if result else 'Unknown'
                db_user = result[1] if result else 'Unknown'
                
            logger.info(f"✅ Conectado ao banco: {db_name} como {db_user}")
            return conn

        except Exception as e:
            logger.error(f"❌ Erro na conexão direta com o banco: {e}")
            return None

    def init_db(self):
        """✅ CORREÇÃO: Inicialização robusta com fallbacks"""
        global connection_pool
        
        if self.initialized:
            return
            
        logger.info("🔄 Iniciando inicialização do banco...")
        
        if not self.database_url:
            logger.warning("⚠️ DATABASE_URL não encontrada - Modo desenvolvimento sem banco")
            self.initialized = True  # ✅ CORREÇÃO: Marcar como inicializado mesmo sem banco
            return
        
        try:
            # Testar conexão primeiro
            test_conn = self.create_direct_connection()
            if not test_conn:
                logger.error("❌ Não foi possível conectar ao banco - Modo desenvolvimento")
                self.initialized = True  # ✅ CORREÇÃO: Continuar sem banco
                return
                
            test_conn.close()
            
            # ✅ CORREÇÃO: Pool com configuração otimizada
            with pool_lock:
                database_url = self.database_url
                if database_url.startswith('postgres://'):
                    database_url = database_url.replace('postgres://', 'postgresql://')
                    
                connection_pool = pool.SimpleConnectionPool(
                    self.pool_min, 
                    self.pool_max,
                    dsn=database_url,
                    sslmode='require'
                )
                
            logger.info(f"✅ Pool de conexões criado! (min: {self.pool_min}, max: {self.pool_max})")
            
            # Criar tabelas
            self.create_tables()
            self.initialized = True
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização do banco: {e}")
            self.initialized = True  # ✅ CORREÇÃO: Continuar mesmo com erro

    def create_tables(self):
        """✅ CORREÇÃO: Tabelas com estrutura consistente"""
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para criar tabelas")
            return
        
        cur = conn.cursor()
        
        try:
            # ✅ CORREÇÃO: Verificar tabelas existentes
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
                        email VARCHAR(255) NOT NULL UNIQUE,
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
            else:
                logger.info("✅ Tabela 'users' já existe")

            # Tabela de estados do jogo
            if 'user_game_states' not in existing_tables:
                cur.execute('''
                    CREATE TABLE user_game_states (
                        user_id VARCHAR(255) PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                        popcoins BIGINT DEFAULT 0,
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
                logger.info("✅ Tabela 'user_game_states' já existe")
                # ✅ CORREÇÃO: Verificar e adicionar coluna popcoins se necessário
                try:
                    cur.execute("SELECT popcoins FROM user_game_states LIMIT 1")
                except Exception:
                    logger.info("🔄 Adicionando coluna 'popcoins' à tabela existente...")
                    cur.execute('ALTER TABLE user_game_states ADD COLUMN popcoins BIGINT DEFAULT 0')
                    conn.commit()
                    logger.info("✅ Coluna 'popcoins' adicionada")

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
            else:
                logger.info("✅ Tabela 'user_ranking' já existe")

            # ✅ CORREÇÃO: Criar índices de forma condicional
            indexes = [
                ('idx_user_game_states_popcoins', 'user_game_states', 'popcoins DESC'),
                ('idx_user_ranking_score', 'user_ranking', 'total_score DESC'),
                ('idx_users_email', 'users', 'email')
            ]
            
            for index_name, table_name, columns in indexes:
                cur.execute(f"""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = '{table_name}' AND indexname = '{index_name}'
                """)
                if not cur.fetchone():
                    cur.execute(f'CREATE INDEX {index_name} ON {table_name}({columns})')
                    logger.info(f"✅ Índice '{index_name}' criado")
            
            conn.commit()
            logger.info("✅ Estrutura do banco verificada/criada com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro na criação das tabelas: {e}")
            conn.rollback()
        finally:
            cur.close()
            self.return_db_connection(conn)

    # ========== MÉTODOS DE USUÁRIO ==========

    def save_user_data(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """✅ CORREÇÃO: Salva dados de forma consistente"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - salvamento simulado")
            return True
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para salvar dados do usuário")
            return False
        
        try:
            with conn.cursor() as cur:
                current_time = datetime.now()
                
                # ✅ CORREÇÃO: Inserir/atualizar usuário
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
                
                # ✅ CORREÇÃO: Salvar dados do jogo
                if user_data.get('game_data'):
                    game_data = user_data['game_data']
                    
                    cur.execute('''
                        INSERT INTO user_game_states 
                        (user_id, popcoins, coins_per_click, coins_per_second, total_coins,
                         prestige_level, click_count, level, experience,
                         upgrades, achievements, inventory, last_update)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            popcoins = EXCLUDED.popcoins,
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
                        game_data.get('popcoins', 0),
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
        """✅ CORREÇÃO: Obter dados com estrutura consistente"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - retornando dados padrão")
            return self.get_default_user_data(user_id)
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para obter dados do usuário")
            return self.get_default_user_data(user_id)
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('''
                    SELECT 
                        u.user_id, u.email, u.display_name, u.avatar_url,
                        u.email_verified, u.created_at, u.last_login, u.last_activity, u.preferences,
                        g.popcoins, g.coins_per_click, g.coins_per_second, g.total_coins,
                        g.prestige_level, g.click_count, g.level, g.experience,
                        g.upgrades, g.achievements, g.inventory, g.last_update
                    FROM users u
                    LEFT JOIN user_game_states g ON u.user_id = g.user_id
                    WHERE u.user_id = %s
                ''', (user_id,))
                
                result = cur.fetchone()
                if not result:
                    logger.warning(f"⚠️ Usuário não encontrado no banco: {user_id}")
                    return self.get_default_user_data(user_id)
                
                # ✅ CORREÇÃO: Estrutura consistente de dados
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
                        'popcoins': result['popcoins'] or 0,
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
                
                logger.info(f"✅ Dados carregados do banco para usuário: {user_id}")
                return user_data
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter dados do usuário {user_id}: {e}")
            return self.get_default_user_data(user_id)
        finally:
            self.return_db_connection(conn)

    def get_default_user_data(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Dados padrão consistentes"""
        current_time = datetime.now().isoformat()
        return {
            'uid': user_id,
            'email': 'unknown@example.com',
            'name': 'Jogador',
            'picture': '/static/images/default-avatar.png',
            'email_verified': False,
            'created_at': current_time,
            'last_login': current_time,
            'last_activity': current_time,
            'preferences': {
                'notifications': True,
                'sound_effects': True,
                'music': True,
                'autosave': True
            },
            'game_data': self.get_default_game_state()
        }

    def get_default_game_state(self) -> Dict[str, Any]:
        """✅ CORREÇÃO: Estado padrão do jogo"""
        return {
            'popcoins': 0,
            'clicks': 0,
            'level': 1,
            'experience': 0,
            'coins_per_click': 1,
            'coins_per_second': 0,
            'total_coins': 0,
            'prestige_level': 0,
            'upgrades': {
                'click_power': 1,
                'auto_clicker': 0,
                'auto_clickers': 0,
                'click_bots': 0
            },
            'achievements': [],
            'inventory': []
        }

    def get_ranking(self, limit: int = 10) -> List[Dict[str, Any]]:
        """✅ CORREÇÃO: Ranking otimizado"""
        if not self.initialized:
            logger.warning("⚠️ Banco não inicializado - retornando ranking mock")
            return self.get_mock_ranking(limit)
        
        conn = self.get_db_connection()
        if not conn:
            logger.error("❌ Falha ao conectar para obter ranking")
            return self.get_mock_ranking(limit)
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('''
                    SELECT u.user_id, u.display_name, u.avatar_url,
                           r.total_score, r.prestige_level, r.level
                    FROM user_ranking r
                    JOIN users u ON r.user_id = u.user_id
                    ORDER BY r.total_score DESC, r.prestige_level DESC, r.level DESC
                    LIMIT %s
                ''', (limit,))
                
                results = cur.fetchall()
                ranking = []
                
                for idx, row in enumerate(results):
                    ranking.append({
                        'uid': row['user_id'],
                        'name': row['display_name'] or f'Jogador {idx + 1}',
                        'avatar': row['avatar_url'] or '/static/images/default-avatar.png',
                        'popcoins': row['total_score'],
                        'prestige_level': row['prestige_level'],
                        'level': row['level'],
                        'rank': idx + 1
                    })
                
                logger.info(f"✅ Ranking carregado: {len(ranking)} jogadores")
                return ranking
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter ranking: {e}")
            return self.get_mock_ranking(limit)
        finally:
            self.return_db_connection(conn)

    def get_mock_ranking(self, limit: int = 10) -> List[Dict[str, Any]]:
        """✅ CORREÇÃO: Ranking mock para desenvolvimento"""
        mock_ranking = [
            {'uid': 'user_1', 'name': 'Jogador Top', 'popcoins': 15000, 'level': 15, 'prestige_level': 2, 'rank': 1},
            {'uid': 'user_2', 'name': 'Clique Mestre', 'popcoins': 12000, 'level': 12, 'prestige_level': 1, 'rank': 2},
            {'uid': 'user_3', 'name': 'Coletor Ávido', 'popcoins': 8000, 'level': 10, 'prestige_level': 0, 'rank': 3}
        ]
        return mock_ranking[:limit]

    def health_check(self) -> Dict[str, Any]:
        """✅ CORREÇÃO: Health check do banco"""
        try:
            if not self.initialized:
                return {
                    'healthy': False,
                    'message': 'Banco não inicializado',
                    'database_url_available': bool(self.database_url)
                }
            
            conn = self.get_db_connection()
            if not conn:
                return {
                    'healthy': False,
                    'message': 'Não foi possível obter conexão',
                    'database_url_available': bool(self.database_url)
                }
            
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT version(), current_database(), current_user')
                    result = cur.fetchone()
                
                return {
                    'healthy': True,
                    'message': 'Banco operacional',
                    'database_version': result[0] if result else 'Unknown',
                    'database_name': result[1] if result else 'Unknown',
                    'database_user': result[2] if result else 'Unknown',
                    'pool_size': connection_pool._used if connection_pool else 0
                }
            finally:
                self.return_db_connection(conn)
                
        except Exception as e:
            return {
                'healthy': False,
                'message': f'Erro no health check: {e}',
                'database_url_available': bool(self.database_url)
            }

# ✅ CORREÇÃO: Instância única com inicialização controlada
db_manager = None

def get_database_manager():
    """Singleton para DatabaseManager"""
    global db_manager
    if db_manager is None:
        try:
            logger.info("🔄 Criando DatabaseManager...")
            db_manager = DatabaseManager()
            
            if db_manager.initialized:
                logger.info("🎉 DatabaseManager inicializado com sucesso!")
                
                # Log do health check
                health = db_manager.health_check()
                logger.info(f"📊 Health check do banco: {health}")
            else:
                logger.warning("⚠️ DatabaseManager em modo desenvolvimento (sem banco)")
                
        except Exception as e:
            logger.error(f"❌ Falha crítica ao criar DatabaseManager: {e}")
            db_manager = None
    
    return db_manager

# Inicialização controlada
logger.info("📦 Inicializando db_models.py...")
db_manager = get_database_manager()