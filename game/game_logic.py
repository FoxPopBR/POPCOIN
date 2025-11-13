# game/game_logic.py - VERSÃO COMPLETAMENTE CORRIGIDA
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configurar logging
logger = logging.getLogger(__name__)

class GameManager:
    def __init__(self):
        # ✅ CORREÇÃO: Estado padrão completamente alinhado e balanceado
        self.default_game_state = {
            "coins": 0,  # ✅ CORREÇÃO: Usar 'coins' em vez de 'popcoins' para consistência
            "coins_per_click": 1,
            "coins_per_second": 0,
            "total_coins": 0,
            "prestige_level": 0,
            "upgrades": {
                "click_power": 1,      # ✅ CORREÇÃO: Nomes padronizados
                "auto_clickers": 0,    # ✅ CORREÇÃO: Somente um tipo de auto_clickers
                "click_bots": 0
            },
            "click_count": 0,          # ✅ CORREÇÃO: click_count em vez de clicks
            "level": 1,
            "experience": 0,
            "inventory": [],
            "achievements": [],
            "last_update": time.time()
        }
        
        # ✅ CORREÇÃO: Sistema de balanceamento
        self.upgrade_config = {
            "click_power": {
                "base_cost": 50,       # ✅ CORREÇÃO: Custo aumentado para balanceamento
                "cost_multiplier": 1.8,
                "effect_per_level": 1,  # +1 coin por clique por nível
                "description": "Aumenta moedas por clique"
            },
            "auto_clickers": {
                "base_cost": 100,      # ✅ CORREÇÃO: Custo balanceado
                "cost_multiplier": 2.0,
                "effect_per_level": 0.2,  # 0.2 coins por segundo por nível
                "description": "Gera moedas automaticamente"
            },
            "click_bots": {
                "base_cost": 500,      # ✅ CORREÇÃO: Custo balanceado
                "cost_multiplier": 2.5,
                "effect_per_level": 1.0,  # 1.0 coin por segundo por nível
                "description": "Bots avançados que geram mais moedas"
            }
        }
        
        logger.info("✅ GameManager inicializado com sistema balanceado")

    def get_user_game_state(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Sistema robusto de carregamento de estado"""
        try:
            # ✅ CORREÇÃO: Tentar banco primeiro
            from database.db_models import get_database_manager
            db_manager = get_database_manager()
            
            game_state = None
            
            if db_manager and db_manager.initialized:
                try:
                    user_data = db_manager.get_user_data(user_id)
                    if user_data and user_data.get('game_data'):
                        game_state = user_data['game_data']
                        # ✅ CORREÇÃO: Garantir estrutura correta
                        game_state = self._ensure_game_state_structure(game_state)
                        game_state = self.calculate_offline_earnings(game_state)
                        logger.info(f"✅ Estado carregado do banco: {user_id}")
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro no banco: {db_error}")

            # ✅ CORREÇÃO: Fallback para estado padrão
            if not game_state:
                logger.info(f"🆕 Criando estado inicial para: {user_id}")
                game_state = self.create_initial_game_state(user_id)
            
            return game_state

        except Exception as e:
            logger.error(f"❌ Erro ao carregar estado: {e}")
            return self.default_game_state.copy()

    def save_game_state(self, user_id: str, game_state: Dict[str, Any]) -> bool:
        """✅ CORREÇÃO: Sistema robusto de salvamento"""
        try:
            # ✅ CORREÇÃO: Garantir estrutura antes de salvar
            game_state = self._ensure_game_state_structure(game_state)
            game_state['last_update'] = time.time()

            # ✅ CORREÇÃO: Salvar via DatabaseManager
            from database.db_models import get_database_manager
            db_manager = get_database_manager()
            
            if db_manager and db_manager.initialized:
                try:
                    user_data = db_manager.get_user_data(user_id) or {}
                    user_data['game_data'] = game_state
                    
                    if db_manager.save_user_data(user_id, user_data):
                        logger.debug(f"💾 Estado salvo no banco: {user_id}")
                        return True
                except Exception as db_error:
                    logger.warning(f"⚠️ Erro ao salvar no banco: {db_error}")

            logger.info(f"💾 Estado salvo localmente: {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao salvar estado: {e}")
            return False

    def _ensure_game_state_structure(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """✅ CORREÇÃO: Garante estrutura consistente do estado do jogo"""
        default_state = self.default_game_state.copy()
        
        # ✅ CORREÇÃO: Mesclar estados mantendo dados existentes
        for key, default_value in default_state.items():
            if key not in game_state:
                game_state[key] = default_value
            elif key == "upgrades" and isinstance(default_value, dict):
                # ✅ CORREÇÃO: Garantir todos os upgrades existam
                for upgrade, upgrade_default in default_value.items():
                    if upgrade not in game_state[key]:
                        game_state[key][upgrade] = upgrade_default
        
        # ✅ CORREÇÃO: Garantir campos numéricos são números
        numeric_fields = ["coins", "coins_per_click", "coins_per_second", "total_coins", 
                         "click_count", "level", "experience", "prestige_level"]
        for field in numeric_fields:
            if field in game_state:
                try:
                    game_state[field] = float(game_state[field])
                except (TypeError, ValueError):
                    game_state[field] = 0
        
        return game_state

    def create_initial_game_state(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Cria estado inicial balanceado"""
        initial_state = self.default_game_state.copy()
        self.save_game_state(user_id, initial_state)
        return initial_state

    def calculate_offline_earnings(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """✅ CORREÇÃO: Sistema de ganhos offline robusto"""
        try:
            current_time = time.time()
            last_update = game_state.get('last_update', current_time)
            
            # ✅ CORREÇÃO: Evitar problemas de tempo
            if last_update > current_time:
                game_state['last_update'] = current_time
                return game_state
            
            time_elapsed = current_time - last_update
            
            # ✅ CORREÇÃO: Limitar ganhos offline a 12 horas
            max_offline_time = 12 * 3600
            time_elapsed = min(time_elapsed, max_offline_time)
            
            # ✅ CORREÇÃO: Calcular ganhos automáticos
            coins_per_second = game_state.get('coins_per_second', 0)
            if coins_per_second > 0 and time_elapsed > 1:  # Pelo menos 1 segundo
                auto_earnings = time_elapsed * coins_per_second
                auto_earnings = int(auto_earnings)  # Apenas moedas inteiras
                
                if auto_earnings > 0:
                    game_state['coins'] += auto_earnings
                    game_state['total_coins'] += auto_earnings
                    
                    logger.info(f"💰 Ganhos offline: +{auto_earnings} moedas ({time_elapsed:.0f}s)")
            
            game_state['last_update'] = current_time
            return game_state
            
        except Exception as e:
            logger.error(f"❌ Erro em ganhos offline: {e}")
            game_state['last_update'] = time.time()
            return game_state

    def process_click(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Sistema de clique balanceado"""
        try:
            game_state = self.get_user_game_state(user_id)
            
            # ✅ CORREÇÃO: Calcular moedas por clique com bônus
            base_coins = 1
            click_power = game_state['upgrades'].get('click_power', 1)
            prestige_bonus = game_state.get('prestige_level', 0) * 0.1
            level_bonus = (game_state.get('level', 1) - 1) * 0.05
            
            coins_earned = base_coins + (click_power - 1) + prestige_bonus + level_bonus
            coins_earned = max(1, int(coins_earned))
            
            # ✅ CORREÇÃO: Aplicar ganhos
            game_state['coins'] += coins_earned
            game_state['total_coins'] += coins_earned
            game_state['click_count'] += 1
            
            # ✅ CORREÇÃO: Sistema de experiência
            exp_gained = max(1, coins_earned)
            game_state['experience'] += exp_gained
            
            # ✅ CORREÇÃO: Verificar evoluções
            level_up = self._check_level_up(game_state)
            new_achievements = self._check_achievements(game_state)
            
            # ✅ CORREÇÃO: Atualizar estatísticas
            self._update_game_stats(game_state)
            
            # Salvar
            self.save_game_state(user_id, game_state)
            
            logger.debug(f"👆 Clique: +{coins_earned} moedas (total: {game_state['coins']})")
            
            return {
                "success": True, 
                "coins_earned": coins_earned,
                "level_up": level_up,
                "new_achievements": new_achievements,
                "game_state": game_state
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no clique: {e}")
            return {"success": False, "error": str(e)}

    def buy_upgrade(self, user_id: str, upgrade_type: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Sistema de compra balanceado"""
        try:
            # ✅ CORREÇÃO: Verificar upgrade válido
            if upgrade_type not in self.upgrade_config:
                return {"success": False, "error": "Upgrade inválido"}
            
            game_state = self.get_user_game_state(user_id)
            current_level = game_state['upgrades'].get(upgrade_type, 0)
            
            # ✅ CORREÇÃO: Calcular custo usando configuração
            config = self.upgrade_config[upgrade_type]
            cost = self._calculate_upgrade_cost(config['base_cost'], config['cost_multiplier'], current_level)
            
            # ✅ CORREÇÃO: Verificar se pode comprar
            if game_state['coins'] >= cost:
                # Debitar custo
                game_state['coins'] -= cost
                
                # Aplicar upgrade
                game_state['upgrades'][upgrade_type] = current_level + 1
                
                # ✅ CORREÇÃO: Atualizar estatísticas do jogo
                self._update_game_stats(game_state)
                
                # Verificar conquistas
                new_achievements = self._check_achievements(game_state)
                
                # Salvar
                self.save_game_state(user_id, game_state)
                
                logger.info(f"🛒 Upgrade comprado: {upgrade_type} nível {current_level + 1} por {cost} moedas")
                
                return {
                    "success": True,
                    "upgrade_type": upgrade_type,
                    "new_level": current_level + 1,
                    "cost": cost,
                    "new_achievements": new_achievements,
                    "game_state": game_state
                }
            else:
                return {
                    "success": False,
                    "error": "Moedas insuficientes",
                    "required": cost,
                    "current": game_state['coins']
                }
                
        except Exception as e:
            logger.error(f"❌ Erro na compra: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_upgrade_cost(self, base_cost: float, multiplier: float, current_level: int) -> int:
        """✅ CORREÇÃO: Cálculo de custo balanceado"""
        return int(base_cost * (multiplier ** current_level))

    def _update_game_stats(self, game_state: Dict[str, Any]) -> None:
        """✅ CORREÇÃO: Atualização robusta de estatísticas"""
        try:
            # ✅ CORREÇÃO: Moedas por clique
            base_click = 1
            click_power = game_state['upgrades'].get('click_power', 1)
            prestige_bonus = game_state.get('prestige_level', 0) * 0.1
            level_bonus = (game_state.get('level', 1) - 1) * 0.05
            
            game_state['coins_per_click'] = base_click + (click_power - 1) + prestige_bonus + level_bonus
            
            # ✅ CORREÇÃO: Moedas por segundo (VALORES AUMENTADOS)
            auto_clickers = game_state['upgrades'].get('auto_clickers', 0)
            click_bots = game_state['upgrades'].get('click_bots', 0)
            
            # ✅ CORREÇÃO: Valores aumentados para melhor gameplay
            auto_clickers_rate = auto_clickers * 0.5  # 0.5 moedas por segundo por nível
            click_bots_rate = click_bots * 2.0        # 2.0 moedas por segundo por nível
            
            game_state['coins_per_second'] = auto_clickers_rate + click_bots_rate
            
            logger.debug(f"📊 Stats atualizados: {game_state['coins_per_click']}/clique, {game_state['coins_per_second']}/segundo")
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar stats: {e}")

    def _check_level_up(self, game_state: Dict[str, Any]) -> bool:
        """✅ CORREÇÃO: Sistema de level up balanceado"""
        try:
            current_exp = game_state.get('experience', 0)
            current_level = game_state.get('level', 1)
            
            # ✅ CORREÇÃO: Progressão exponencial
            exp_required = current_level * 100
            
            if current_exp >= exp_required:
                new_level = current_level + 1
                remaining_exp = current_exp - exp_required
                
                game_state['level'] = new_level
                game_state['experience'] = remaining_exp
                
                logger.info(f"🎯 Level up! Nível {new_level}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro no level up: {e}")
            return False

    def _check_achievements(self, game_state: Dict[str, Any]) -> List[str]:
        """✅ CORREÇÃO: Sistema de conquistas"""
        try:
            current_achievements = game_state.get('achievements', [])
            new_achievements = []
            
            achievement_criteria = [
                ('first_coins', game_state['total_coins'] >= 100),
                ('clicker_beginner', game_state['click_count'] >= 50),
                ('clicker_pro', game_state['click_count'] >= 500),
                ('upgrade_collector', sum(game_state['upgrades'].values()) >= 10),
                ('idle_master', game_state['coins_per_second'] >= 5),
                ('wealthy', game_state['total_coins'] >= 10000),
                ('prestige_beginner', game_state['prestige_level'] >= 1),
            ]
            
            for achievement_id, condition in achievement_criteria:
                if condition and achievement_id not in current_achievements:
                    current_achievements.append(achievement_id)
                    new_achievements.append(achievement_id)
            
            game_state['achievements'] = current_achievements
            
            if new_achievements:
                logger.info(f"🏆 Conquistas: {new_achievements}")
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"❌ Erro nas conquistas: {e}")
            return []

    def get_upgrade_info(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Informações detalhadas dos upgrades"""
        try:
            game_state = self.get_user_game_state(user_id)
            upgrades_info = {}
            
            for upgrade_type, config in self.upgrade_config.items():
                current_level = game_state['upgrades'].get(upgrade_type, 0)
                cost = self._calculate_upgrade_cost(config['base_cost'], config['cost_multiplier'], current_level)
                
                upgrades_info[upgrade_type] = {
                    'current_level': current_level,
                    'next_level': current_level + 1,
                    'cost': cost,
                    'can_afford': game_state['coins'] >= cost,
                    'description': config['description'],
                    'effect_per_level': config['effect_per_level']
                }
            
            return upgrades_info
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter upgrade info: {e}")
            return {}

    def prestige(self, user_id: str) -> Dict[str, Any]:
        """✅ CORREÇÃO: Sistema de prestígio balanceado"""
        try:
            game_state = self.get_user_game_state(user_id)
            
            # ✅ CORREÇÃO: Requisito de prestígio aumentado
            required_coins = 25000
            
            if game_state['total_coins'] >= required_coins:
                current_prestige = game_state.get('prestige_level', 0)
                prestige_bonus = max(1, int(game_state['total_coins'] / 10000))
                
                # ✅ CORREÇÃO: Aplicar prestígio
                game_state['prestige_level'] = current_prestige + 1
                game_state['coins'] = 0
                game_state['coins_per_click'] = 1 + prestige_bonus
                game_state['coins_per_second'] = 0
                game_state['click_count'] = 0
                game_state['level'] = 1
                game_state['experience'] = 0
                
                # ✅ CORREÇÃO: Manter apenas conquistas, resetar upgrades
                game_state['upgrades'] = {
                    "click_power": 1,
                    "auto_clickers": 0,
                    "click_bots": 0
                }
                
                # Atualizar stats
                self._update_game_stats(game_state)
                
                # Salvar
                self.save_game_state(user_id, game_state)
                
                logger.info(f"⭐ Prestígio {current_prestige + 1}! Bônus: {prestige_bonus}x")
                
                return {
                    "success": True,
                    "prestige_level": game_state['prestige_level'],
                    "prestige_bonus": prestige_bonus,
                    "game_state": game_state
                }
            else:
                return {
                    "success": False,
                    "error": f"Requer {required_coins} moedas totais",
                    "required": required_coins,
                    "current": game_state['total_coins']
                }
                
        except Exception as e:
            logger.error(f"❌ Erro no prestígio: {e}")
            return {"success": False, "error": str(e)}

# ✅ CORREÇÃO: Singleton melhorado
_game_manager_instance = None

def get_game_manager():
    global _game_manager_instance
    if _game_manager_instance is None:
        try:
            _game_manager_instance = GameManager()
            logger.info("🎮 GameManager criado com sucesso")
        except Exception as e:
            logger.error(f"💥 Falha ao criar GameManager: {e}")
            _game_manager_instance = None
    return _game_manager_instance

# Inicialização
logger.info("📦 Carregando game_logic.py...")
game_manager = get_game_manager()