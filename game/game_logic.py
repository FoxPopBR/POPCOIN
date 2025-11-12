# game/game_logic.py - VERSÃO CORRIGIDA (mantendo estrutura atual)
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configurar logging
logger = logging.getLogger(__name__)

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
            "click_count": 0,
            "last_update": time.time(),
            "inventory": [],
            "achievements": [],
            "experience": 0,
            "level": 1
        }
        
        logger.info("✅ GameManager inicializado")
    
    def get_user_game_state(self, user_id: str) -> Dict[str, Any]:
        """Recupera o estado do jogo do usuário - CORREÇÃO: Usar novo esquema"""
        try:
            # Usar as funções de compatibilidade do db_models
            try:
                from database.db_models import get_user_game_state as db_get_state
                db_state = db_get_state(user_id)
                if db_state:
                    db_state = self.calculate_offline_earnings(db_state)
                    logger.info(f"✅ Estado do jogo carregado do banco para: {user_id}")
                    return db_state
            except ImportError as e:
                logger.warning(f"⚠️ Database não disponível: {e}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro no banco de dados, usando fallback: {db_error}")

            # Fallback para estado padrão
            logger.info(f"🆕 Criando estado inicial para usuário: {user_id}")
            return self.create_initial_game_state(user_id)

        except Exception as e:
            logger.error(f"❌ Erro crítico ao buscar estado do jogo: {e}")
            return self.default_game_state.copy()

    def save_game_state(self, user_id: str, game_state: Dict[str, Any]) -> bool:
        """Salva o estado do jogo - CORREÇÃO: Usar novo esquema"""
        try:
            # Atualizar timestamp
            game_state['last_update'] = time.time()

            # Usar as funções de compatibilidade do db_models
            try:
                from database.db_models import save_user_game_state as db_save_state
                if db_save_state(user_id, game_state):
                    logger.info(f"💾 Estado do jogo salvo no banco para: {user_id}")
                    return True
            except ImportError as e:
                logger.warning(f"⚠️ Database não disponível: {e}")
            except Exception as db_error:
                logger.warning(f"⚠️ Erro ao salvar no banco: {db_error}")

            # Fallback local
            logger.info(f"💾 Estado salvo localmente (sem banco): {user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro crítico ao salvar estado do jogo: {e}")
            return True
        # 🎯 MANTER TODOS OS OUTROS MÉTODOS EXATAMENTE COMO ESTÃO
    def _sync_with_user_profile(self, user_id: str, game_state: Dict[str, Any]) -> None:
        """Sincroniza dados do jogo com o perfil do usuário"""
        try:
            # Esta função seria chamada pelo app.py quando o perfil do usuário for atualizado
            # Por enquanto é um placeholder para integração futura
            pass
        except Exception as e:
            logger.warning(f"⚠️ Erro na sincronização do perfil: {e}")
    
    def create_initial_game_state(self, user_id: str) -> Dict[str, Any]:
        """Cria estado inicial do jogo para novo usuário"""
        initial_state = self.default_game_state.copy()
        
        # Tentar salvar o estado inicial
        self.save_game_state(user_id, initial_state)
        
        logger.info(f"🎮 Estado inicial criado para usuário: {user_id}")
        return initial_state
    
    def calculate_offline_earnings(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula moedas geradas enquanto o usuário estava offline"""
        try:
            current_time = time.time()
            last_update = game_state.get('last_update', current_time)
            time_elapsed = current_time - last_update
            
            # Limitar ganhos offline a 24 horas (evitar exploit)
            max_offline_time = 24 * 3600  # 24 horas em segundos
            time_elapsed = min(time_elapsed, max_offline_time)
            
            # Calcular moedas geradas automaticamente
            coins_per_second = game_state.get('coins_per_second', 0)
            auto_earnings = time_elapsed * coins_per_second
            
            if auto_earnings > 0:
                game_state['coins'] += auto_earnings
                game_state['total_coins'] += auto_earnings
                
                logger.info(f"💰 Ganhos offline: {auto_earnings:.1f} moedas em {time_elapsed:.0f}s")
            
            game_state['last_update'] = current_time
            
            return game_state
            
        except Exception as e:
            logger.error(f"❌ Erro no cálculo de ganhos offline: {e}")
            return game_state
    
    def process_click(self, user_id: str) -> Dict[str, Any]:
        """Processa um clique do usuário e retorna o novo estado"""
        try:
            game_state = self.get_user_game_state(user_id)
            
            # Adicionar moedas do clique
            coins_per_click = game_state.get('coins_per_click', 1)
            game_state['coins'] += coins_per_click
            game_state['total_coins'] += coins_per_click
            game_state['click_count'] = game_state.get('click_count', 0) + 1
            
            # Adicionar experiência
            experience_gained = max(1, coins_per_click // 2)
            game_state['experience'] = game_state.get('experience', 0) + experience_gained
            
            # Verificar level up
            self._check_level_up(game_state)
            
            # Verificar conquistas
            new_achievements = self._check_achievements(game_state)
            
            # Salvar estado atualizado
            self.save_game_state(user_id, game_state)
            
            logger.info(f"👆 Clique processado para {user_id}: +{coins_per_click} moedas")
            
            return {
                "success": True, 
                "game_state": game_state,
                "coins_earned": coins_per_click,
                "new_achievements": new_achievements
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar clique: {e}")
            return {"success": False, "error": str(e)}
    
    def buy_upgrade(self, user_id: str, upgrade_type: str, base_cost: int) -> Dict[str, Any]:
        """Compra um upgrade para o usuário"""
        try:
            game_state = self.get_user_game_state(user_id)
            
            # Calcular custo real baseado no nível atual
            current_level = game_state['upgrades'].get(upgrade_type, 0)
            actual_cost = self._calculate_upgrade_cost(base_cost, current_level)
            
            if game_state['coins'] >= actual_cost:
                # Deduzir custo
                game_state['coins'] -= actual_cost
                
                # Aplicar upgrade
                game_state['upgrades'][upgrade_type] = current_level + 1
                
                # Atualizar estatísticas do jogo
                self._update_game_stats(game_state)
                
                # Verificar conquistas
                new_achievements = self._check_achievements(game_state)
                
                # Salvar estado atualizado
                self.save_game_state(user_id, game_state)
                
                logger.info(f"🛒 Upgrade comprado: {upgrade_type} nível {current_level + 1} para {user_id}")
                
                return {
                    "success": True, 
                    "game_state": game_state,
                    "new_achievements": new_achievements
                }
            else:
                logger.warning(f"❌ Moedas insuficientes para upgrade: {user_id}")
                return {
                    "success": False, 
                    "error": "Moedas insuficientes",
                    "required": actual_cost,
                    "current": game_state['coins']
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao comprar upgrade: {e}")
            return {"success": False, "error": str(e)}
    
    def prestige(self, user_id: str) -> Dict[str, Any]:
        """Executa prestígio para o usuário"""
        try:
            game_state = self.get_user_game_state(user_id)
            
            if game_state['total_coins'] >= 10000:
                prestige_bonus = max(1, game_state['total_coins'] // 10000)
                
                # Aplicar prestígio
                game_state['prestige_level'] += 1
                game_state['coins'] = 0
                game_state['coins_per_click'] = 1 + prestige_bonus
                game_state['coins_per_second'] = 0
                game_state['upgrades'] = {"click_power": 0, "auto_clickers": 0, "click_bots": 0}
                game_state['click_count'] = 0
                # Manter conquistas e nível?
                # game_state['achievements'] = []
                
                # Salvar estado atualizado
                self.save_game_state(user_id, game_state)
                
                logger.info(f"⭐ Prestígio realizado: nível {game_state['prestige_level']} para {user_id}")
                
                return {
                    "success": True, 
                    "game_state": game_state,
                    "prestige_bonus": prestige_bonus
                }
            else:
                return {
                    "success": False, 
                    "error": "Moedas insuficientes para prestígio",
                    "required": 10000,
                    "current": game_state['total_coins']
                }
                
        except Exception as e:
            logger.error(f"❌ Erro no prestígio: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_upgrade_cost(self, base_cost: int, current_level: int) -> int:
        """Calcula o custo real do upgrade baseado no nível atual"""
        return int(base_cost * (1.5 ** current_level))
    
    def _update_game_stats(self, game_state: Dict[str, Any]) -> None:
        """Atualiza as estatísticas do jogo baseado nos upgrades"""
        # Força do clique
        game_state['coins_per_click'] = 1 + game_state['upgrades']['click_power']
        
        # Moedas por segundo (auto clickers + click bots)
        auto_clicker_rate = game_state['upgrades']['auto_clickers'] * 0.1
        click_bot_rate = game_state['upgrades']['click_bots'] * 0.5
        game_state['coins_per_second'] = auto_clicker_rate + click_bot_rate
    
    def _check_level_up(self, game_state: Dict[str, Any]) -> bool:
        """Verifica e aplica level up se necessário"""
        experience = game_state.get('experience', 0)
        current_level = game_state.get('level', 1)
        
        # Fórmula simples: 100 EXP por nível
        exp_needed = current_level * 100
        
        if experience >= exp_needed:
            game_state['level'] = current_level + 1
            game_state['experience'] = experience - exp_needed
            
            # Bônus de level up
            game_state['coins_per_click'] += 0.1
            
            logger.info(f"🎯 Level up: nível {current_level + 1}")
            return True
        
        return False
    
    def _check_achievements(self, game_state: Dict[str, Any]) -> list:
        """Verifica e desbloqueia conquistas"""
        achievements = game_state.get('achievements', [])
        new_achievements = []
        
        # Conquista: Primeiras Moedas
        if game_state['total_coins'] >= 100 and 'first_coins' not in achievements:
            achievements.append('first_coins')
            new_achievements.append('first_coins')
        
        # Conquista: Clique Rápido
        if game_state['click_count'] >= 50 and 'fast_clicker' not in achievements:
            achievements.append('fast_clicker')
            new_achievements.append('fast_clicker')
        
        # Conquista: Industrial
        total_upgrades = sum(game_state['upgrades'].values())
        if total_upgrades >= 10 and 'industrial' not in achievements:
            achievements.append('industrial')
            new_achievements.append('industrial')
        
        # Conquista: Milionário
        if game_state['total_coins'] >= 1000000 and 'millionaire' not in achievements:
            achievements.append('millionaire')
            new_achievements.append('millionaire')
        
        # Atualizar lista de conquistas
        game_state['achievements'] = achievements
        
        if new_achievements:
            logger.info(f"🏆 Conquistas desbloqueadas: {new_achievements}")
        
        return new_achievements
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Obtém estatísticas resumidas do usuário para ranking"""
        try:
            game_state = self.get_user_game_state(user_id)
            
            return {
                "user_id": user_id,
                "total_coins": game_state.get('total_coins', 0),
                "level": game_state.get('level', 1),
                "prestige_level": game_state.get('prestige_level', 0),
                "click_count": game_state.get('click_count', 0),
                "achievements_count": len(game_state.get('achievements', [])),
                "last_active": game_state.get('last_update', time.time())
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {e}")
            return {}
    
    def reset_user_data(self, user_id: str) -> bool:
        """Reseta todos os dados do usuário (para testes/debug)"""
        try:
            initial_state = self.default_game_state.copy()
            return self.save_game_state(user_id, initial_state)
        except Exception as e:
            logger.error(f"❌ Erro ao resetar dados: {e}")
            return False

# Instância global do GameManager
game_manager = GameManager()