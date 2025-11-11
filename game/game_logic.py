# game/game_logic.py - VERSÃO OTIMIZADA
import json
import time
from database.db_models import get_db_connection, return_db_connection

class GameManager:
    def __init__(self):
        self.default_game_state = {
            "coins": 0,
            "coins_per_click": 1,
            "coins_per_second": 0,
            "total_coins": 0,
            "prestige_level": 0,
            "upgrades": {
                "click_power": 1,
                "auto_clickers": 0,
                "click_bots": 0
            },
            "last_update": time.time(),
            "inventory": [],
            "achievements": []
        }
    
    def get_user_game_state(self, user_id):
        """Recupera o estado do jogo do usuário usando pool"""
        conn = get_db_connection()
        if not conn:
            print("❌ No database connection in get_user_game_state")
            return self.default_game_state.copy()
            
        cur = conn.cursor()
        
        try:
            cur.execute(
                'SELECT game_data FROM user_game_states WHERE user_id = %s',
                (user_id,)
            )
            result = cur.fetchone()
            
            if result:
                game_state = json.loads(result[0])
                game_state = self.calculate_offline_earnings(game_state)
                print(f"✅ Game state loaded for user {user_id}")
                return game_state
            else:
                print(f"🆕 Creating initial game state for user {user_id}")
                return self.create_initial_game_state(user_id)
                
        except Exception as e:
            print(f"❌ Erro ao buscar estado do jogo: {e}")
            return self.default_game_state.copy()
        finally:
            cur.close()
            return_db_connection(conn)
    
    def save_game_state(self, user_id, game_state):
        """Salva o estado do jogo usando pool"""
        conn = get_db_connection()
        if not conn:
            print("❌ No database connection in save_game_state")
            return False
            
        cur = conn.cursor()
        
        try:
            game_state['last_update'] = time.time()  # Atualizar timestamp
            game_state_json = json.dumps(game_state)
            
            cur.execute(
                '''INSERT INTO user_game_states (user_id, game_data) 
                   VALUES (%s, %s)
                   ON CONFLICT (user_id) 
                   DO UPDATE SET game_data = EXCLUDED.game_data, updated_at = CURRENT_TIMESTAMP''',
                (user_id, game_state_json)
            )
            conn.commit()
            print(f"✅ Game state saved for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar estado do jogo: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            return_db_connection(conn)
    
    def create_initial_game_state(self, user_id):
        """Cria estado inicial do jogo para novo usuário"""
        initial_state = self.default_game_state.copy()
        self.save_game_state(user_id, initial_state)
        return initial_state
    
    def calculate_offline_earnings(self, game_state):
        """Calcula moedas geradas enquanto o usuário estava offline"""
        current_time = time.time()
        last_update = game_state.get('last_update', current_time)
        time_elapsed = current_time - last_update
        
        # Calcular moedas geradas automaticamente
        auto_earnings = time_elapsed * game_state.get('coins_per_second', 0)
        game_state['coins'] += auto_earnings
        game_state['total_coins'] += auto_earnings
        game_state['last_update'] = current_time
        
        return game_state
    
    def process_click(self, user_id):
        """Processa um clique do usuário"""
        game_state = self.get_user_game_state(user_id)
        
        # Adicionar moedas do clique
        coins_earned = game_state.get('coins_per_click', 1)
        game_state['coins'] += coins_earned
        game_state['total_coins'] += coins_earned
        
        self.save_game_state(user_id, game_state)
        return game_state
    
    def buy_upgrade(self, user_id, upgrade_type, cost):
        """Compra um upgrade para o usuário"""
        game_state = self.get_user_game_state(user_id)
        
        if game_state['coins'] >= cost:
            game_state['coins'] -= cost
            
            if upgrade_type == 'click_power':
                game_state['upgrades']['click_power'] += 1
                game_state['coins_per_click'] = game_state['upgrades']['click_power']
            
            elif upgrade_type == 'auto_clicker':
                game_state['upgrades']['auto_clickers'] += 1
                game_state['coins_per_second'] += 0.1
            
            elif upgrade_type == 'click_bot':
                game_state['upgrades']['click_bots'] += 1
                game_state['coins_per_second'] += 1
            
            self.save_game_state(user_id, game_state)
            return {"success": True, "game_state": game_state}
        else:
            return {"success": False, "error": "Moedas insuficientes"}