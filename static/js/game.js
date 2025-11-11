// Gerenciamento principal do jogo
class PopCoinGame {
    constructor() {
        this.gameState = {
            coins: 0,
            coins_per_click: 1,
            coins_per_second: 0,
            total_coins: 0,
            prestige_level: 0,
            upgrades: {
                click_power: 1,
                auto_clickers: 0,
                click_bots: 0
            },
            click_count: 0,
            last_update: Date.now()
        };
        
        this.isLoading = true;
        this.autoSaveInterval = null;
        this.gameLoopInterval = null;
        
        this.init();
    }

    async init() {
        await this.loadGameState();
        this.setupEventListeners();
        this.startGameLoop();
        this.startAutoSave();
        this.hideLoading();
    }

    async loadGameState() {
        try {
            const response = await fetch('/api/game/state');
            const data = await response.json();
            
            if (!data.error) {
                this.gameState = { ...this.gameState, ...data };
                this.updateUI();
            } else {
                console.error('Erro ao carregar estado do jogo:', data.error);
            }
        } catch (error) {
            console.error('Erro ao carregar jogo:', error);
        }
    }

    async saveGameState() {
        try {
            await fetch('/api/game/state', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.gameState)
            });
        } catch (error) {
            console.error('Erro ao salvar jogo:', error);
        }
    }

    setupEventListeners() {
        // Botão de clique principal
        const clickButton = document.getElementById('click-button');
        clickButton.addEventListener('click', () => this.handleClick());

        // Botões de upgrade
        document.querySelectorAll('.buy-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const upgradeItem = e.target.closest('.upgrade-item');
                const upgradeType = upgradeItem.dataset.upgrade;
                const cost = parseInt(button.dataset.cost);
                this.buyUpgrade(upgradeType, cost);
            });
        });

        // Prevenir duplo clique de seleção de texto
        clickButton.addEventListener('mousedown', (e) => e.preventDefault());
    }

    handleClick() {
        // Adicionar moedas
        this.gameState.coins += this.gameState.coins_per_click;
        this.gameState.total_coins += this.gameState.coins_per_click;
        this.gameState.click_count++;
        
        // Animação de clique
        this.showClickBonus(this.gameState.coins_per_click);
        this.animateCoin();
        
        // Atualizar UI
        this.updateUI();
        
        // Verificar conquistas
        this.checkAchievements();
    }

    showClickBonus(amount) {
        const bonusElement = document.getElementById('click-bonus');
        bonusElement.textContent = `+${amount}`;
        bonusElement.classList.add('show');
        
        setTimeout(() => {
            bonusElement.classList.remove('show');
        }, 1000);
    }

    animateCoin() {
        const coin = document.getElementById('coin-animation');
        coin.classList.add('animate');
        
        setTimeout(() => {
            coin.classList.remove('animate');
        }, 300);
    }

    async buyUpgrade(upgradeType, baseCost) {
        const currentLevel = this.gameState.upgrades[upgradeType];
        const cost = this.calculateUpgradeCost(baseCost, currentLevel);
        
        if (this.gameState.coins >= cost) {
            // Deduzir custo
            this.gameState.coins -= cost;
            
            // Aplicar upgrade
            switch (upgradeType) {
                case 'click_power':
                    this.gameState.upgrades.click_power++;
                    this.gameState.coins_per_click = this.gameState.upgrades.click_power;
                    break;
                    
                case 'auto_clicker':
                    this.gameState.upgrades.auto_clickers++;
                    this.gameState.coins_per_second += 0.1;
                    break;
                    
                case 'click_bot':
                    this.gameState.upgrades.click_bots++;
                    this.gameState.coins_per_second += 1;
                    break;
            }
            
            // Atualizar UI
            this.updateUI();
            
            // Verificar conquistas
            this.checkAchievements();
            
        } else {
            this.showMessage('Moedas insuficientes!', 'error');
        }
    }

    calculateUpgradeCost(baseCost, currentLevel) {
        // Custo aumenta exponencialmente
        return Math.floor(baseCost * Math.pow(1.5, currentLevel));
    }

    updateUI() {
        // Atualizar estatísticas principais
        document.getElementById('coins-count').textContent = Math.floor(this.gameState.coins);
        document.getElementById('coins-per-click').textContent = this.gameState.coins_per_click;
        document.getElementById('coins-per-second').textContent = this.gameState.coins_per_second.toFixed(1);
        document.getElementById('prestige-level').textContent = this.gameState.prestige_level;

        // Atualizar informações de upgrades
        document.getElementById('click-power-level').textContent = this.gameState.upgrades.click_power;
        document.getElementById('click-power-bonus').textContent = this.gameState.upgrades.click_power;
        document.getElementById('auto-clicker-count').textContent = this.gameState.upgrades.auto_clickers;
        document.getElementById('auto-clicker-bonus').textContent = (this.gameState.upgrades.auto_clickers * 0.1).toFixed(1);
        document.getElementById('click-bot-count').textContent = this.gameState.upgrades.click_bots;
        document.getElementById('click-bot-bonus').textContent = this.gameState.upgrades.click_bots;

        // Atualizar custos dos botões
        document.querySelectorAll('.buy-button').forEach(button => {
            const upgradeItem = button.closest('.upgrade-item');
            const upgradeType = upgradeItem.dataset.upgrade;
            const baseCost = parseInt(button.dataset.cost);
            const currentLevel = this.gameState.upgrades[upgradeType];
            const cost = this.calculateUpgradeCost(baseCost, currentLevel);
            
            button.querySelector('.cost').textContent = cost;
            
            // Desabilitar botão se não tiver moedas suficientes
            button.disabled = this.gameState.coins < cost;
        });
    }

    checkAchievements() {
        // Implementar lógica de conquistas
        // Por enquanto, é um placeholder
    }

    showMessage(message, type = 'info') {
        // Implementar sistema de mensagens
        console.log(`${type}: ${message}`);
    }

    startGameLoop() {
        this.gameLoopInterval = setInterval(() => {
            // Gerar moedas automáticas
            if (this.gameState.coins_per_second > 0) {
                const now = Date.now();
                const timeElapsed = (now - this.gameState.last_update) / 1000; // em segundos
                const autoEarnings = timeElapsed * this.gameState.coins_per_second;
                
                this.gameState.coins += autoEarnings;
                this.gameState.total_coins += autoEarnings;
                this.gameState.last_update = now;
                
                this.updateUI();
            }
        }, 100); // Atualizar a cada 100ms para smooth animation
    }

    startAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveGameState();
        }, 30000); // Salvar a cada 30 segundos
    }

    hideLoading() {
        this.isLoading = false;
        document.getElementById('loading-overlay').style.display = 'none';
    }

    // Limpar intervals quando a página for fechada
    destroy() {
        if (this.gameLoopInterval) clearInterval(this.gameLoopInterval);
        if (this.autoSaveInterval) clearInterval(this.autoSaveInterval);
        this.saveGameState();
    }
}

// Inicializar o jogo quando a página carregar
let game;

document.addEventListener('DOMContentLoaded', () => {
    game = new PopCoinGame();
});

// Salvar quando o usuário sair da página
window.addEventListener('beforeunload', () => {
    if (game) {
        game.destroy();
    }
});