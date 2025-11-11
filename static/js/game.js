// Gerenciamento principal do jogo - VERSÃO COMPLETA
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
            last_update: Date.now() / 1000,
            inventory: [],
            achievements: []
        };
        
        this.isLoading = true;
        this.autoSaveInterval = null;
        this.gameLoopInterval = null;
        
        this.init();
    }

    async init() {
        console.log("🎮 Inicializando jogo...");
        
        // Verificar autenticação antes de carregar o jogo
        if (window.authManager) {
            let waitCount = 0;
            while (!window.authManager.authChecked && waitCount < 50) {
                await new Promise(resolve => setTimeout(resolve, 100));
                waitCount++;
            }
            
            if (!window.authManager.isAuthenticated) {
                console.log("❌ Usuário não autenticado, redirecionando...");
                window.location.href = '/';
                return;
            }
        }

        console.log("✅ Usuário autenticado, carregando jogo...");
        await this.loadGameState();
        this.setupEventListeners();
        this.startGameLoop();
        this.startAutoSave();
        this.hideLoading();
    }

    async loadGameState() {
        try {
            console.log("📥 Carregando estado do jogo...");
            const response = await fetch('/api/game/state');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.error('❌ Erro do servidor:', data.error);
                return;
            }
            
            // Mesclar o estado carregado com o estado padrão
            this.gameState = { 
                ...this.gameState, 
                ...data,
                upgrades: { ...this.gameState.upgrades, ...data.upgrades }
            };
            
            // Calcular ganhos offline se houver tempo desde a última atualização
            this.calculateOfflineEarnings();
            
            this.updateUI();
            console.log("✅ Estado do jogo carregado:", this.gameState);
            
        } catch (error) {
            console.error('❌ Erro ao carregar jogo:', error);
            this.showMessage('Erro ao carregar o jogo. Tentando novamente...', 'error');
            
            // Tentar novamente após 3 segundos
            setTimeout(() => this.loadGameState(), 3000);
        }
    }

    async saveGameState() {
        try {
            this.gameState.last_update = Date.now() / 1000;
            
            const response = await fetch('/api/game/state', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.gameState)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                console.log('💾 Estado do jogo salvo');
            } else {
                console.error('❌ Erro ao salvar:', result.error);
            }
        } catch (error) {
            console.error('❌ Erro ao salvar jogo:', error);
        }
    }

    calculateOfflineEarnings() {
        const now = Date.now() / 1000;
        const timeDiff = now - this.gameState.last_update;
        
        if (timeDiff > 60 && this.gameState.coins_per_second > 0) { // Mais de 1 minuto offline
            const offlineEarnings = timeDiff * this.gameState.coins_per_second;
            this.gameState.coins += offlineEarnings;
            this.gameState.total_coins += offlineEarnings;
            
            console.log(`💰 Ganhos offline: ${offlineEarnings.toFixed(1)} moedas (${timeDiff.toFixed(0)}s)`);
            
            if (offlineEarnings > 0) {
                this.showMessage(`💰 Ganhos offline: +${offlineEarnings.toFixed(0)} moedas!`, 'success');
            }
        }
    }

    setupEventListeners() {
        // Botão de clique principal
        const clickButton = document.getElementById('click-button');
        if (clickButton) {
            clickButton.addEventListener('click', () => this.handleClick());
            clickButton.addEventListener('mousedown', (e) => e.preventDefault()); // Prevenir seleção de texto
        }

        // Botões de upgrade
        document.querySelectorAll('.buy-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const upgradeItem = e.target.closest('.upgrade-item');
                if (!upgradeItem) return;
                
                const upgradeType = upgradeItem.dataset.upgrade;
                const baseCost = parseInt(button.dataset.cost);
                this.buyUpgrade(upgradeType, baseCost);
            });
        });

        // Botão de prestígio (se existir)
        const prestigeButton = document.getElementById('prestige-button');
        if (prestigeButton) {
            prestigeButton.addEventListener('click', () => this.prestige());
        }

        // Salvar quando o usuário sair da página
        window.addEventListener('beforeunload', () => {
            this.destroy();
        });

        console.log("✅ Event listeners configurados");
    }

    handleClick() {
        // Adicionar moedas
        const coinsEarned = this.gameState.coins_per_click;
        this.gameState.coins += coinsEarned;
        this.gameState.total_coins += coinsEarned;
        this.gameState.click_count++;
        
        // Animação de clique
        this.showClickBonus(coinsEarned);
        this.animateCoin();
        
        // Atualizar UI
        this.updateUI();
        
        // Verificar conquistas
        this.checkAchievements();
        
        // Salvar a cada 10 cliques
        if (this.gameState.click_count % 10 === 0) {
            this.saveGameState();
        }
    }

    showClickBonus(amount) {
        const bonusElement = document.getElementById('click-bonus');
        if (!bonusElement) return;
        
        bonusElement.textContent = `+${amount}`;
        bonusElement.classList.add('show');
        
        // Posição aleatória
        const randomX = (Math.random() * 100 - 50);
        bonusElement.style.transform = `translateX(${randomX}px)`;
        
        setTimeout(() => {
            bonusElement.classList.remove('show');
        }, 1000);
    }

    animateCoin() {
        const coin = document.getElementById('coin-animation');
        if (!coin) return;
        
        coin.classList.add('animate');
        
        setTimeout(() => {
            coin.classList.remove('animate');
        }, 300);
    }

    async buyUpgrade(upgradeType, baseCost) {
        const currentLevel = this.gameState.upgrades[upgradeType] || 0;
        const cost = this.calculateUpgradeCost(baseCost, currentLevel);
        
        if (this.gameState.coins >= cost) {
            // Deduzir custo
            this.gameState.coins -= cost;
            
            // Aplicar upgrade
            this.gameState.upgrades[upgradeType] = currentLevel + 1;
            
            switch (upgradeType) {
                case 'click_power':
                    this.gameState.coins_per_click = 1 + this.gameState.upgrades.click_power;
                    break;
                    
                case 'auto_clicker':
                    this.gameState.coins_per_second = 0.1 * this.gameState.upgrades.auto_clickers;
                    break;
                    
                case 'click_bot':
                    this.gameState.coins_per_second += 0.5; // Cada bot adiciona 0.5/s
                    break;
            }
            
            // Efeitos visuais
            this.showMessage(`✅ Upgrade comprado: ${this.getUpgradeName(upgradeType)} Nv. ${this.gameState.upgrades[upgradeType]}`, 'success');
            
            // Atualizar UI
            this.updateUI();
            
            // Verificar conquistas
            this.checkAchievements();
            
            // Salvar estado
            await this.saveGameState();
            
        } else {
            this.showMessage('❌ Moedas insuficientes!', 'error');
            // Efeito visual de shake no botão
            const button = document.querySelector(`[data-upgrade="${upgradeType}"] .buy-button`);
            if (button) {
                button.classList.add('shake');
                setTimeout(() => button.classList.remove('shake'), 500);
            }
        }
    }

    calculateUpgradeCost(baseCost, currentLevel) {
        // Custo aumenta exponencialmente
        return Math.floor(baseCost * Math.pow(1.5, currentLevel));
    }

    getUpgradeName(upgradeType) {
        const names = {
            'click_power': 'Força do Clique',
            'auto_clicker': 'Clique Automático',
            'click_bot': 'Bot de Clique'
        };
        return names[upgradeType] || upgradeType;
    }

    updateUI() {
        // Atualizar estatísticas principais
        this.updateElementText('coins-count', Math.floor(this.gameState.coins));
        this.updateElementText('coins-per-click', this.gameState.coins_per_click);
        this.updateElementText('coins-per-second', this.gameState.coins_per_second.toFixed(1));
        this.updateElementText('prestige-level', this.gameState.prestige_level);
        this.updateElementText('total-clicks', this.gameState.click_count);

        // Atualizar informações de upgrades
        this.updateElementText('click-power-level', this.gameState.upgrades.click_power);
        this.updateElementText('click-power-bonus', this.gameState.upgrades.click_power);
        this.updateElementText('auto-clicker-count', this.gameState.upgrades.auto_clickers);
        this.updateElementText('auto-clicker-bonus', (this.gameState.upgrades.auto_clickers * 0.1).toFixed(1));
        this.updateElementText('click-bot-count', this.gameState.upgrades.click_bots);
        this.updateElementText('click-bot-bonus', (this.gameState.upgrades.click_bots * 0.5).toFixed(1));

        // Atualizar custos dos botões
        document.querySelectorAll('.upgrade-item').forEach(item => {
            const upgradeType = item.dataset.upgrade;
            const button = item.querySelector('.buy-button');
            const costElement = button.querySelector('.cost');
            const baseCost = parseInt(button.dataset.cost);
            const currentLevel = this.gameState.upgrades[upgradeType] || 0;
            const cost = this.calculateUpgradeCost(baseCost, currentLevel);
            
            if (costElement) {
                costElement.textContent = cost;
            }
            
            // Desabilitar botão se não tiver moedas suficientes
            button.disabled = this.gameState.coins < cost;
            
            // Adicionar classe visual se não puder comprar
            if (this.gameState.coins < cost) {
                button.classList.add('cant-afford');
            } else {
                button.classList.remove('cant-afford');
            }
        });

        // Atualizar conquistas
        this.updateAchievements();
    }

    updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    checkAchievements() {
        const achievements = [];
        
        // Conquista: Primeiras moedas
        if (this.gameState.total_coins >= 100 && !this.gameState.achievements.includes('first_coins')) {
            achievements.push({ id: 'first_coins', name: '💰 Primeiras Moedas', description: 'Ganhe 100 moedas' });
        }
        
        // Conquista: Clique rápido
        if (this.gameState.click_count >= 50 && !this.gameState.achievements.includes('fast_clicker')) {
            achievements.push({ id: 'fast_clicker', name: '⚡ Clique Rápido', description: 'Faça 50 cliques' });
        }
        
        // Conquista: Industrial
        const totalUpgrades = Object.values(this.gameState.upgrades).reduce((a, b) => a + b, 0);
        if (totalUpgrades >= 10 && !this.gameState.achievements.includes('industrial')) {
            achievements.push({ id: 'industrial', name: '🏭 Industrial', description: 'Tenha 10 upgrades' });
        }
        
        // Adicionar novas conquistas
        achievements.forEach(achievement => {
            if (!this.gameState.achievements.includes(achievement.id)) {
                this.gameState.achievements.push(achievement.id);
                this.showMessage(`🏆 Conquista desbloqueada: ${achievement.name}`, 'achievement');
                console.log(`🏆 Conquista: ${achievement.name}`);
            }
        });
    }

    updateAchievements() {
        const achievementsList = document.getElementById('achievements-list');
        if (!achievementsList) return;
        
        const allAchievements = [
            { id: 'first_coins', name: '💰 Primeiras Moedas', description: 'Ganhe 100 moedas' },
            { id: 'fast_clicker', name: '⚡ Clique Rápido', description: 'Faça 50 cliques' },
            { id: 'industrial', name: '🏭 Industrial', description: 'Tenha 10 upgrades' }
        ];
        
        achievementsList.innerHTML = '';
        
        allAchievements.forEach(achievement => {
            const achieved = this.gameState.achievements.includes(achievement.id);
            const achievementElement = document.createElement('div');
            achievementElement.className = `achievement ${achieved ? 'unlocked' : 'locked'}`;
            achievementElement.innerHTML = `
                <strong>${achievement.name}</strong>
                <span>${achievement.description}</span>
                ${achieved ? '<span class="achievement-badge">✅</span>' : ''}
            `;
            achievementsList.appendChild(achievementElement);
        });
    }

    prestige() {
        // Sistema de prestígio básico
        if (this.gameState.total_coins >= 10000) {
            const prestigeBonus = Math.floor(this.gameState.total_coins / 10000);
            
            if (confirm(`Fazer prestígio? Você ganhará ${prestigeBonus}x multiplicador mas resetará seu progresso!`)) {
                this.gameState.prestige_level += 1;
                this.gameState.coins = 0;
                this.gameState.coins_per_click = 1 + prestigeBonus;
                this.gameState.coins_per_second = 0;
                this.gameState.upgrades = { click_power: 0, auto_clickers: 0, click_bots: 0 };
                this.gameState.click_count = 0;
                
                this.showMessage(`🎉 Prestígio ${this.gameState.prestige_level}! Multiplicador: ${prestigeBonus}x`, 'prestige');
                this.updateUI();
                this.saveGameState();
            }
        } else {
            this.showMessage('❌ Precisa de 10,000 moedas totais para fazer prestígio!', 'error');
        }
    }

    showMessage(message, type = 'info') {
        // Criar elemento de mensagem se não existir
        let messageContainer = document.getElementById('message-container');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.id = 'message-container';
            messageContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                max-width: 300px;
            `;
            document.body.appendChild(messageContainer);
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        messageElement.textContent = message;
        messageElement.style.cssText = `
            background: ${type === 'error' ? '#ff4444' : type === 'success' ? '#44ff44' : type === 'achievement' ? '#ffaa00' : '#4444ff'};
            color: white;
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 5px;
            animation: slideIn 0.3s ease-out;
        `;
        
        messageContainer.appendChild(messageElement);
        
        // Remover após 3 segundos
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    if (messageElement.parentNode) {
                        messageElement.parentNode.removeChild(messageElement);
                    }
                }, 300);
            }
        }, 3000);
        
        console.log(`💬 ${type}: ${message}`);
    }

    startGameLoop() {
        this.gameLoopInterval = setInterval(() => {
            // Gerar moedas automáticas
            if (this.gameState.coins_per_second > 0) {
                const autoEarnings = this.gameState.coins_per_second / 10; // Dividido por 10 porque roda 10x por segundo
                
                this.gameState.coins += autoEarnings;
                this.gameState.total_coins += autoEarnings;
                
                // Atualizar a cada 10 frames para performance
                if (Math.random() < 0.1) {
                    this.updateUI();
                }
            }
        }, 100); // Atualizar a cada 100ms para animação suave
    }

    startAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveGameState();
        }, 30000); // Salvar a cada 30 segundos
    }

    hideLoading() {
        this.isLoading = false;
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
    }

    // Limpar intervals quando a página for fechada
    destroy() {
        if (this.gameLoopInterval) {
            clearInterval(this.gameLoopInterval);
            this.gameLoopInterval = null;
        }
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
        this.saveGameState();
        console.log('🎮 Jogo finalizado');
    }
}

// Inicializar o jogo quando a página carregar
let game;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎮 Inicializando PopCoin Game...');
    game = new PopCoinGame();
});

// Adicionar estilos CSS para animações
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .shake {
        animation: shake 0.5s;
    }
    
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
    
    .cant-afford {
        opacity: 0.6;
        filter: grayscale(1);
    }
    
    .achievement.unlocked {
        background: linear-gradient(45deg, #ffd700, #ffaa00);
        color: #000;
    }
    
    .achievement.locked {
        background: #333;
        color: #888;
    }
    
    .achievement-badge {
        float: right;
        font-weight: bold;
    }
`;
document.head.appendChild(style);