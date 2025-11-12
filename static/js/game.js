// static/js/game.js - VERSÃO COMPLETA CORRIGIDA E INTEGRADA
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
        this.lastSaveTime = 0;
        this.saveCooldown = 5000; // 5 segundos entre saves
        
        this.init();
    }

    async init() {
        console.log("🎮 Inicializando jogo...");
        
        // ✅ CORREÇÃO: Verificação de autenticação mais robusta
        if (!await this.checkAuthentication()) {
            return;
        }

        console.log("✅ Usuário autenticado, carregando jogo...");
        await this.loadGameState();
        this.setupEventListeners();
        this.startGameLoop();
        this.startAutoSave();
        this.hideLoading();
        
        this.addProfileLink();
    }

    async checkAuthentication() {
        // ✅ CORREÇÃO: Verificação mais robusta com timeout
        let attempts = 0;
        while (!window.authManager && attempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (!window.authManager) {
            console.error("❌ AuthManager não carregado");
            this.showMessage("Erro de autenticação. Redirecionando...", "error");
            setTimeout(() => window.location.href = '/', 2000);
            return false;
        }

        // Aguardar verificação de autenticação
        let authCheckAttempts = 0;
        while (!window.authManager.authChecked && authCheckAttempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            authCheckAttempts++;
        }
        
        if (!window.authManager.isUserAuthenticated()) {
            console.log("❌ Usuário não autenticado, redirecionando...");
            this.showMessage("Você precisa estar logado para jogar. Redirecionando...", "error");
            setTimeout(() => window.location.href = '/', 2000);
            return false;
        }

        return true;
    }

    async loadGameState() {
        try {
            console.log("📥 Carregando estado do jogo...");
            
            // ✅ CORREÇÃO: Verificar autenticação antes de carregar
            if (!window.authManager || !window.authManager.isUserAuthenticated()) {
                throw new Error("Usuário não autenticado");
            }

            const response = await fetch('/api/game/state');
            
            if (response.status === 401) {
                this.showMessage('Sessão expirada. Redirecionando...', 'error');
                setTimeout(() => window.location.href = '/', 2000);
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.error('❌ Erro do servidor:', data.error);
                this.showMessage('Erro ao carregar jogo: ' + data.error, 'error');
                return;
            }
            
            // ✅ CORREÇÃO: Melhor tratamento de estado vazio
            if (Object.keys(data).length === 0 || !data.coins) {
                console.log("📭 Nenhum estado salvo encontrado, usando estado padrão");
                this.updateUI();
                return;
            }
            
            // Mesclar o estado carregado com o estado padrão
            this.gameState = { 
                ...this.gameState, 
                ...data,
                upgrades: { ...this.gameState.upgrades, ...(data.upgrades || {}) }
            };
            
            this.calculateOfflineEarnings();
            this.updateUI();
            console.log("✅ Estado do jogo carregado:", this.gameState);
            
        } catch (error) {
            console.error('❌ Erro ao carregar jogo:', error);
            
            if (error.message.includes("autenticado") || error.message.includes("autorizado")) {
                this.showMessage('Sessão expirada. Redirecionando...', 'error');
                setTimeout(() => window.location.href = '/', 2000);
                return;
            }
            
            this.showMessage('Erro ao carregar o jogo. Tentando continuar offline...', 'warning');
            setTimeout(() => this.loadGameState(), 5000);
        }
    }

    async saveGameState(force = false) {
        const now = Date.now();
        if (!force && now - this.lastSaveTime < this.saveCooldown) {
            return;
        }
        
        try {
            // ✅ CORREÇÃO: Verificar autenticação antes de salvar
            if (!window.authManager || !window.authManager.isUserAuthenticated()) {
                console.warn("⚠️ Usuário não autenticado, ignorando save");
                return;
            }

            this.gameState.last_update = Date.now() / 1000;
            this.lastSaveTime = now;
            
            const response = await fetch('/api/game/state', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.gameState)
            });
            
            if (response.status === 401) {
                this.showMessage('Sessão expirada. Faça login novamente.', 'error');
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                console.log('💾 Estado do jogo salvo');
                this.updateSaveStatus('✅ Jogo salvo');
            } else {
                console.error('❌ Erro ao salvar:', result.error);
            }
        } catch (error) {
            console.error('❌ Erro ao salvar jogo:', error);
            this.updateSaveStatus('❌ Erro ao salvar');
        }
    }

    calculateOfflineEarnings() {
        const now = Date.now() / 1000;
        const timeDiff = now - this.gameState.last_update;
        
        if (timeDiff > 60 && this.gameState.coins_per_second > 0) {
            const offlineEarnings = Math.min(timeDiff * this.gameState.coins_per_second, 3600 * this.gameState.coins_per_second);
            this.gameState.coins += offlineEarnings;
            this.gameState.total_coins += offlineEarnings;
            
            console.log(`💰 Ganhos offline: ${offlineEarnings.toFixed(1)} moedas (${timeDiff.toFixed(0)}s)`);
            
            if (offlineEarnings > 10) {
                this.showMessage(`💰 Ganhos offline: +${Math.floor(offlineEarnings)} moedas!`, 'success');
            }
        }
    }

    setupEventListeners() {
        // Botão de clique principal
        const clickButton = document.getElementById('click-button');
        if (clickButton) {
            clickButton.addEventListener('click', () => this.handleClick());
            clickButton.addEventListener('mousedown', (e) => e.preventDefault());
            
            // Efeitos de hover
            clickButton.addEventListener('mouseenter', () => {
                clickButton.style.transform = 'scale(1.05)';
            });
            clickButton.addEventListener('mouseleave', () => {
                clickButton.style.transform = 'scale(1)';
            });
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

        // Botão de prestígio
        const prestigeButton = document.getElementById('prestige-button');
        if (prestigeButton) {
            prestigeButton.addEventListener('click', () => this.prestige());
        }

        // Salvar quando o usuário sair da página
        window.addEventListener('beforeunload', () => {
            this.destroy();
        });

        // Salvar quando a página for ocultada
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.saveGameState(true);
            }
        });

        console.log("✅ Event listeners configurados");
    }

    addProfileLink() {
        // Adicionar link para o perfil no header do jogo
        const gameTitle = document.querySelector('.game-title');
        if (gameTitle && !document.getElementById('profile-link')) {
            const profileLink = document.createElement('a');
            profileLink.id = 'profile-link';
            profileLink.href = '/profile';
            profileLink.className = 'btn btn-secondary';
            profileLink.innerHTML = '👤 Meu Perfil';
            profileLink.style.marginLeft = '10px';
            gameTitle.appendChild(profileLink);
        }
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
        
        // Salvar a cada 25 cliques
        if (this.gameState.click_count % 25 === 0) {
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
        const randomY = -30 - (Math.random() * 20);
        bonusElement.style.transform = `translate(${randomX}px, ${randomY}px)`;
        
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
        }, 200);
    }

    async buyUpgrade(upgradeType, baseCost) {
        const currentLevel = this.gameState.upgrades[upgradeType] || 0;
        const cost = this.calculateUpgradeCost(baseCost, currentLevel);
        
        if (this.gameState.coins >= cost) {
            // Deduzir custo
            this.gameState.coins -= cost;
            
            // Aplicar upgrade
            this.gameState.upgrades[upgradeType] = currentLevel + 1;
            
            // Atualizar estatísticas do jogo
            this.updateGameStats();
            
            this.showMessage(`✅ Upgrade comprado: ${this.getUpgradeName(upgradeType)} Nv. ${this.gameState.upgrades[upgradeType]}`, 'success');
            this.updateUI();
            this.checkAchievements();
            await this.saveGameState(true);
            
        } else {
            this.showMessage('❌ Moedas insuficientes!', 'error');
            const button = document.querySelector(`[data-upgrade="${upgradeType}"] .buy-button`);
            if (button) {
                button.classList.add('shake');
                setTimeout(() => button.classList.remove('shake'), 500);
            }
        }
    }

    updateGameStats() {
        // Atualizar coins_per_click baseado no upgrade de click_power
        this.gameState.coins_per_click = 1 + this.gameState.upgrades.click_power;
        
        // Atualizar coins_per_second baseado nos upgrades
        this.gameState.coins_per_second = (this.gameState.upgrades.auto_clickers * 0.1) + 
                                         (this.gameState.upgrades.click_bots * 0.5);
    }

    calculateUpgradeCost(baseCost, currentLevel) {
        return Math.floor(baseCost * Math.pow(1.5, currentLevel));
    }

    getUpgradeName(upgradeType) {
        const names = {
            'click_power': 'Força do Clique',
            'auto_clickers': 'Clique Automático',
            'click_bots': 'Bot de Clique'
        };
        return names[upgradeType] || upgradeType;
    }

    updateUI() {
        // Atualizar estatísticas principais
        this.updateElementText('coins-count', this.formatNumber(Math.floor(this.gameState.coins)));
        this.updateElementText('coins-per-click', this.gameState.coins_per_click);
        this.updateElementText('coins-per-second', this.gameState.coins_per_second.toFixed(1));
        this.updateElementText('prestige-level', this.gameState.prestige_level);
        this.updateElementText('total-clicks', this.formatNumber(this.gameState.click_count));

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
                costElement.textContent = this.formatNumber(cost);
            }
            
            // Desabilitar botão se não tiver moedas suficientes
            button.disabled = this.gameState.coins < cost;
            
            if (this.gameState.coins < cost) {
                button.classList.add('cant-afford');
            } else {
                button.classList.remove('cant-afford');
            }
        });

        // Atualizar botão de prestígio
        this.updatePrestigeButton();

        // Atualizar conquistas
        this.updateAchievements();
    }

    updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    updatePrestigeButton() {
        const prestigeButton = document.getElementById('prestige-button');
        if (prestigeButton) {
            const prestigeBonus = Math.floor(this.gameState.total_coins / 10000);
            prestigeButton.textContent = `Fazer Prestígio (${prestigeBonus}x)`;
            prestigeButton.disabled = this.gameState.total_coins < 10000;
            
            if (prestigeButton.disabled) {
                prestigeButton.classList.add('cant-afford');
            } else {
                prestigeButton.classList.remove('cant-afford');
            }
        }
    }

    updateSaveStatus(message) {
        const saveStatus = document.getElementById('save-status');
        if (saveStatus) {
            saveStatus.textContent = message;
            setTimeout(() => {
                if (saveStatus.textContent === message) {
                    saveStatus.textContent = '💾 Salvamento automático ativo';
                }
            }, 3000);
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

        // Conquista: Milionário
        if (this.gameState.total_coins >= 1000000 && !this.gameState.achievements.includes('millionaire')) {
            achievements.push({ id: 'millionaire', name: '💎 Milionário', description: 'Acumule 1 milhão de moedas' });
        }
        
        // Adicionar novas conquistas
        achievements.forEach(achievement => {
            if (!this.gameState.achievements.includes(achievement.id)) {
                this.gameState.achievements.push(achievement.id);
                this.showMessage(`🏆 Conquista desbloqueada: ${achievement.name}`, 'achievement');
                console.log(`🏆 Conquista: ${achievement.name}`);
                
                this.saveGameState(true);
            }
        });
    }

    updateAchievements() {
        const achievementsList = document.getElementById('achievements-list');
        if (!achievementsList) return;
        
        const allAchievements = [
            { id: 'first_coins', name: '💰 Primeiras Moedas', description: 'Ganhe 100 moedas' },
            { id: 'fast_clicker', name: '⚡ Clique Rápido', description: 'Faça 50 cliques' },
            { id: 'industrial', name: '🏭 Industrial', description: 'Tenha 10 upgrades' },
            { id: 'millionaire', name: '💎 Milionário', description: 'Acumule 1 milhão de moedas' }
        ];
        
        achievementsList.innerHTML = '';
        
        allAchievements.forEach(achievement => {
            const achieved = this.gameState.achievements.includes(achievement.id);
            const achievementElement = document.createElement('div');
            achievementElement.className = `achievement ${achieved ? 'unlocked' : 'locked'}`;
            achievementElement.innerHTML = `
                <div class="achievement-icon">${achieved ? '✅' : '🔒'}</div>
                <div class="achievement-info">
                    <strong>${achievement.name}</strong>
                    <span>${achievement.description}</span>
                </div>
            `;
            achievementsList.appendChild(achievementElement);
        });
    }

    prestige() {
        if (this.gameState.total_coins >= 10000) {
            const prestigeBonus = Math.floor(this.gameState.total_coins / 10000);
            
            if (confirm(`Fazer prestígio? Você ganhará ${prestigeBonus}x multiplicador mas resetará seu progresso!\n\nIsso inclui:\n- Todas as moedas\n- Todos os upgrades\n- Todas as conquistas\n\nVocê manterá apenas seu nível de prestígio.`)) {
                this.gameState.prestige_level += 1;
                this.gameState.coins = 0;
                this.gameState.coins_per_click = 1 + prestigeBonus;
                this.gameState.coins_per_second = 0;
                this.gameState.upgrades = { click_power: 0, auto_clickers: 0, click_bots: 0 };
                this.gameState.click_count = 0;
                this.gameState.achievements = [];
                
                this.showMessage(`🎉 Prestígio ${this.gameState.prestige_level}! Multiplicador: ${prestigeBonus}x`, 'prestige');
                this.updateUI();
                this.saveGameState(true);
            }
        } else {
            this.showMessage('❌ Precisa de 10,000 moedas totais para fazer prestígio!', 'error');
        }
    }

    showMessage(message, type = 'info') {
        // Usar o sistema de mensagens do authManager se disponível
        if (window.authManager && window.authManager.showMessage) {
            window.authManager.showMessage(message, type);
            return;
        }
        
        // Fallback: sistema de mensagens próprio
        let messageContainer = document.getElementById('message-container');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.id = 'message-container';
            messageContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
            `;
            document.body.appendChild(messageContainer);
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        messageElement.textContent = message;
        messageElement.style.cssText = `
            background: ${this.getMessageColor(type)};
            color: white;
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 8px;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideInRight 0.3s ease-out;
        `;
        
        messageContainer.appendChild(messageElement);
        
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    if (messageElement.parentNode) {
                        messageElement.remove();
                    }
                }, 300);
            }
        }, 5000);
        
        console.log(`💬 ${type}: ${message}`);
    }

    getMessageColor(type) {
        const colors = {
            'error': '#dc3545',
            'success': '#28a745',
            'warning': '#ffc107',
            'info': '#17a2b8',
            'achievement': '#ff6b00',
            'prestige': '#9c27b0'
        };
        return colors[type] || colors.info;
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    startGameLoop() {
        this.gameLoopInterval = setInterval(() => {
            if (this.gameState.coins_per_second > 0) {
                const autoEarnings = this.gameState.coins_per_second / 10;
                
                this.gameState.coins += autoEarnings;
                this.gameState.total_coins += autoEarnings;
                
                if (Date.now() % 1000 < 100) {
                    this.updateUI();
                }
            }
        }, 100);
    }

    startAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            this.saveGameState();
        }, 30000);
    }

    hideLoading() {
        this.isLoading = false;
        const loadingOverlay = document.getElementById('game-loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        
        this.showMessage('🎮 Jogo carregado! Clique na moeda para começar!', 'success');
    }

    destroy() {
        if (this.gameLoopInterval) {
            clearInterval(this.gameLoopInterval);
            this.gameLoopInterval = null;
        }
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
        
        // ✅ CORREÇÃO: Salvar apenas se autenticado
        if (window.authManager && window.authManager.isUserAuthenticated()) {
            this.saveGameState(true);
        }
        
        console.log('🎮 Jogo finalizado');
    }
}

// ✅ CORREÇÃO: Inicialização mais segura
let game;

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎮 Inicializando PopCoin Game...');
    
    const initGame = async () => {
        let attempts = 0;
        while (!window.authManager && attempts < 50) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }
        
        if (window.authManager && window.authManager.isUserAuthenticated()) {
            game = new PopCoinGame();
        } else {
            console.log('❌ Usuário não autenticado, jogo não iniciado');
        }
    };
    
    initGame();
});

// Adicionar estilos CSS para animações
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
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
        cursor: not-allowed;
    }
    
    .achievement {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .achievement.unlocked {
        background: linear-gradient(45deg, #fff3cd, #ffecb5);
        border: 1px solid #ffeaa7;
        color: #000;
    }
    
    .achievement.locked {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        color: #6c757d;
    }
    
    .achievement-icon {
        font-size: 1.25rem;
    }
    
    .achievement-info {
        display: flex;
        flex-direction: column;
    }
    
    .achievement-info strong {
        font-size: 0.9rem;
    }
    
    .achievement-info span {
        font-size: 0.8rem;
        opacity: 0.8;
    }
    
    @media (max-width: 768px) {
        #profile-link {
            margin-left: 0.5rem !important;
            padding: 0.5rem 0.75rem !important;
            font-size: 0.8rem;
        }
    }
`;
document.head.appendChild(style);