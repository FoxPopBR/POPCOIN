// static/js/auth.js - VERSÃO COMPLETAMENTE CORRIGIDA
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.loginInProgress = false;
        this.syncInProgress = false;
        this.initialized = false;
        
        console.log('🔄 AuthManager inicializando...');
    }

    async init() {
        if (this.initialized) {
            console.log('✅ AuthManager já inicializado');
            return;
        }

        try {
            // ✅ CORREÇÃO: Inicialização SEQUENCIAL e controlada
            await this.initializeFirebase();
            this.setupAuthListeners();
            this.setupEventListeners();
            await this.checkInitialAuth();
            
            this.initialized = true;
            console.log('✅ AuthManager inicializado com sucesso');
        } catch (error) {
            console.error('❌ Falha na inicialização do AuthManager:', error);
            this.showCriticalError('Erro ao carregar sistema de autenticação');
        }
    }

    async initializeFirebase() {
        try {
            console.log('🔥 Inicializando Firebase...');
            
            if (typeof firebase === 'undefined') {
                throw new Error('Firebase não carregado');
            }

            // ✅ CORREÇÃO: Obter configuração UMA VEZ
            const config = await this.getFirebaseConfig();
            
            if (!config || !config.apiKey) {
                throw new Error('Configuração do Firebase não disponível');
            }

            if (!firebase.apps.length) {
                firebase.initializeApp(config);
                console.log('✅ Firebase inicializado com configuração do backend');
            } else {
                console.log('🔁 Firebase já estava inicializado');
            }
            
        } catch (error) {
            console.error('❌ Erro na inicialização do Firebase:', error);
            throw error;
        }
    }

    async getFirebaseConfig() {
        try {
            console.log('📡 Obtendo configuração do Firebase...');
            
            const response = await fetch('/api/auth/firebase-config');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const config = await response.json();
            console.log('✅ Configuração do Firebase obtida');
            return config;
            
        } catch (error) {
            console.error('❌ Erro ao obter configuração:', error);
            return null;
        }
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        // ✅ CORREÇÃO: Listener SIMPLES sem lógica complexa
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? user.email : 'Deslogado');
            
            if (this.loginInProgress) {
                console.log('⏳ Login em andamento, ignorando change...');
                return;
            }
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
    }

    setupEventListeners() {
        // ✅ CORREÇÃO: Event listeners SIMPLES e diretos
        document.addEventListener('click', (e) => {
            const target = e.target;
            
            // Login com Google
            if (target.id === 'loginButton' || target.closest('#loginButton')) {
                e.preventDefault();
                this.loginWithGoogle();
            }
            
            // Logout
            if (target.id === 'logoutButton' || target.closest('#logoutButton')) {
                e.preventDefault();
                this.logout();
            }
            
            // Jogo (apenas logado)
            if ((target.id === 'play-button' || target.closest('#play-button')) && this.isAuthenticated) {
                e.preventDefault();
                this.redirectToGame();
            }
        });
    }

    async checkInitialAuth() {
        try {
            console.log("🔍 Verificando autenticação inicial...");
            
            // ✅ CORREÇÃO: Verificar servidor PRIMEIRO
            const serverAuth = await this.checkServerAuth();
            
            if (!serverAuth) {
                // Se não tem sessão no servidor, verificar Firebase
                await this.checkFirebaseAuth();
            }
            
        } catch (error) {
            console.error('❌ Erro na verificação inicial:', error);
        } finally {
            this.authChecked = true;
            this.hideAuthLoading();
        }
    }

    async checkServerAuth() {
        try {
            console.log("📡 Verificando sessão no servidor...");
            const response = await fetch('/api/auth/status');
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.authenticated && data.user) {
                    console.log("✅ Sessão servidor encontrada:", data.user.email);
                    this.user = data.user;
                    this.isAuthenticated = true;
                    this.updateUI(this.user);
                    return true;
                }
            }
            
            return false;
            
        } catch (error) {
            console.error('❌ Erro ao verificar sessão:', error);
            return false;
        }
    }

    async checkFirebaseAuth() {
        try {
            const user = firebase.auth().currentUser;
            
            if (user) {
                console.log("👤 Usuário no Firebase:", user.email);
                // ✅ CORREÇÃO: Não chamar handleUserLogin aqui - deixar para o listener
                return true;
            }
            
            return false;
            
        } catch (error) {
            console.error('❌ Erro ao verificar Firebase:', error);
            return false;
        }
    }

    async loginWithGoogle() {
        if (this.loginInProgress) {
            console.log('⏳ Login já em andamento...');
            return;
        }

        try {
            this.showLoading('Conectando com Google...');
            this.loginInProgress = true;
            
            console.log('🔐 Iniciando login com Google...');
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google iniciado');
            
        } catch (error) {
            console.error('❌ Erro no login com Google:', error);
            this.hideLoading();
            this.loginInProgress = false;
            
            if (error.code !== 'auth/popup-closed-by-user') {
                this.showMessage('Erro no login: ' + this.getErrorMessage(error), 'error');
            }
        }
    }

    async handleUserLogin(user) {
        if (this.loginInProgress && this.user?.uid === user.uid) {
            console.log('⏳ Login já processado para este usuário');
            return;
        }

        console.log('👤 Processando login:', user.email);
        this.user = user;
        this.loginInProgress = true;
        
        try {
            // ✅ CORREÇÃO: Obter token e sincronizar UMA VEZ
            const token = await user.getIdToken();
            console.log('✅ Token obtido, sincronizando...');
            
            const syncResult = await this.syncWithServer(token);
            
            if (syncResult.success) {
                this.isAuthenticated = true;
                
                // ✅ CORREÇÃO: Atualizar UI com dados do servidor
                this.updateUI(syncResult.user);
                this.saveLocalData(syncResult.user);
                
                console.log('✅ Login sincronizado com servidor');
                
                if (!this.authChecked) {
                    this.showMessage('Login bem-sucedido!', 'success');
                }
                
                // ✅ CORREÇÃO: Redirecionar para PERFIL
                this.handlePostLoginRedirect();
                
            } else {
                throw new Error(syncResult.error || 'Falha na sincronização');
            }
        } catch (error) {
            console.error('❌ Erro ao sincronizar:', error);
            // Em caso de erro, fazer logout para manter consistência
            await firebase.auth().signOut();
            this.showMessage('Erro ao conectar com servidor', 'error');
        } finally {
            this.loginInProgress = false;
            this.hideLoading();
        }
    }

    async syncWithServer(token) {
        if (this.syncInProgress) {
            console.log('⏳ Sincronização já em andamento...');
            return { success: false, error: 'Sincronização em andamento' };
        }

        try {
            this.syncInProgress = true;
            
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ token })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            return result;
            
        } catch (error) {
            console.error('❌ Erro na sincronização:', error);
            return {
                success: false,
                error: error.message
            };
        } finally {
            this.syncInProgress = false;
        }
    }

    saveLocalData(userData) {
        try {
            localStorage.setItem('popcoin_user', JSON.stringify(userData));
            localStorage.setItem('popcoin_last_sync', Date.now().toString());
        } catch (error) {
            console.warn('⚠️ Erro ao salvar dados locais:', error);
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout');
        
        this.user = null;
        this.isAuthenticated = false;
        this.updateUI(null);
        
        this.clearLocalData();
        this.notifyServerLogout();
        this.handlePostLogoutRedirect();
    }

    clearLocalData() {
        try {
            localStorage.removeItem('popcoin_user');
            localStorage.removeItem('popcoin_last_sync');
        } catch (error) {
            console.warn('⚠️ Erro ao limpar dados locais:', error);
        }
    }

    async notifyServerLogout() {
        try {
            await fetch('/api/auth/logout', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            console.log('✅ Servidor notificado do logout');
        } catch (error) {
            console.warn('⚠️ Falha ao notificar servidor:', error);
        }
    }

    async logout() {
        if (this.loginInProgress) {
            console.log('⏳ Operação em andamento...');
            return;
        }

        try {
            console.log('🚪 Iniciando logout...');
            this.showLoading('Saindo...');
            
            await firebase.auth().signOut();
            this.handleUserLogout();
            
            this.showMessage('Logout realizado!', 'success');
            
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            this.showMessage('Erro ao fazer logout', 'error');
            this.handleUserLogout();
        } finally {
            this.hideLoading();
        }
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para:', user ? user.email : 'null');
        
        // ✅ CORREÇÃO: Seletores mais específicos e fallbacks
        const elements = {
            userInfo: document.getElementById('user-info'),
            loginSection: document.getElementById('login-section'),
            authLoading: document.getElementById('auth-loading'),
            userPic: document.getElementById('user-pic'),
            userName: document.getElementById('user-name'),
            gameSection: document.getElementById('game-section'),
            welcomeSection: document.getElementById('welcome-section'),
            profileSection: document.getElementById('profile-section'),
            playButton: document.getElementById('play-button')
        };

        // Esconder loading de auth
        if (elements.authLoading) {
            elements.authLoading.style.display = 'none';
        }

        if (user) {
            // Usuário logado
            if (elements.userPic) {
                elements.userPic.src = user.picture || '/static/images/default-avatar.png';
                elements.userPic.onerror = () => {
                    elements.userPic.src = '/static/images/default-avatar.png';
                };
            }
            if (elements.userName) {
                elements.userName.textContent = user.name || user.email || 'Usuário';
            }
            
            // Mostrar/Esconder elementos
            this.toggleElement(elements.userInfo, true);
            this.toggleElement(elements.loginSection, false);
            this.toggleElement(elements.gameSection, true);
            this.toggleElement(elements.welcomeSection, false);
            this.toggleElement(elements.profileSection, true);
            this.toggleElement(elements.playButton, true);
        } else {
            // Usuário não logado
            this.toggleElement(elements.userInfo, false);
            this.toggleElement(elements.loginSection, true);
            this.toggleElement(elements.gameSection, false);
            this.toggleElement(elements.welcomeSection, true);
            this.toggleElement(elements.profileSection, false);
            this.toggleElement(elements.playButton, false);
        }
    }

    toggleElement(element, show) {
        if (!element) return;
        
        if (show) {
            element.classList.remove('hidden');
            element.style.display = '';
        } else {
            element.classList.add('hidden');
            element.style.display = 'none';
        }
    }

    handlePostLoginRedirect() {
        if (this.redirecting) return;
        
        const currentPath = window.location.pathname;
        
        // ✅ CORREÇÃO: Redirecionar apenas se estiver na página inicial
        if (currentPath === '/' || currentPath === '/index.html') {
            console.log('➡️ Redirecionando para PERFIL...');
            this.redirecting = true;
            
            setTimeout(() => {
                window.location.href = '/profile';
            }, 1000);
        }
    }

    redirectToGame() {
        if (this.redirecting) return;
        
        console.log('🎮 Redirecionando para jogo...');
        this.redirecting = true;
        window.location.href = '/game';
    }

    handlePostLogoutRedirect() {
        if (this.redirecting) return;
        
        const currentPath = window.location.pathname;
        const protectedPaths = ['/game', '/profile'];
        
        if (protectedPaths.includes(currentPath)) {
            console.log('⬅️ Redirecionando para página inicial...');
            this.redirecting = true;
            
            setTimeout(() => {
                window.location.href = '/';
            }, 800);
        }
    }

    showCriticalError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background: #dc3545;
            color: white;
            padding: 1rem;
            text-align: center;
            z-index: 10000;
            font-weight: bold;
        `;
        errorDiv.textContent = message;
        document.body.appendChild(errorDiv);
    }

    hideAuthLoading() {
        const loadingElement = document.getElementById('auth-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }

    showLoading(message = 'Processando...') {
        let loadingEl = document.getElementById('global-loading');
        if (!loadingEl) {
            loadingEl = document.createElement('div');
            loadingEl.id = 'global-loading';
            loadingEl.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                font-size: 1.2rem;
            `;
            document.body.appendChild(loadingEl);
        }
        
        loadingEl.innerHTML = `
            <div style="text-align: center;">
                <div style="width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.3); border-radius: 50%; border-top: 4px solid white; animation: spin 1s linear infinite; margin: 0 auto 1rem;"></div>
                <div>${message}</div>
            </div>
        `;
        loadingEl.style.display = 'flex';
    }

    hideLoading() {
        const loadingEl = document.getElementById('global-loading');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    showMessage(message, type = 'info') {
        console.log(`💬 ${type.toUpperCase()}: ${message}`);
        
        // Implementação simples de mensagem
        alert(`${type.toUpperCase()}: ${message}`);
    }

    getErrorMessage(error) {
        const errorMessages = {
            'auth/popup-closed-by-user': 'Login cancelado.',
            'auth/cancelled-popup-request': 'Login cancelado.',
            'auth/popup-blocked': 'Popup bloqueado. Permita popups para este site.',
            'auth/network-request-failed': 'Erro de conexão. Verifique sua internet.',
        };

        return errorMessages[error.code] || `Erro: ${error.message}`;
    }

    getCurrentUser() {
        return this.user;
    }

    isUserAuthenticated() {
        return this.isAuthenticated;
    }
}

// ✅ CORREÇÃO: Inicialização SIMPLES e controlada
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, preparando AuthManager...');
    
    // Estado inicial
    const authLoading = document.getElementById('auth-loading');
    const loginSection = document.getElementById('login-section');
    
    if (authLoading) authLoading.style.display = 'block';
    if (loginSection) loginSection.style.display = 'none';
    
    // Inicialização com delay para garantir dependências
    setTimeout(() => {
        try {
            if (typeof firebase === 'undefined') {
                throw new Error('Firebase não carregado');
            }
            
            console.log('🎯 Inicializando AuthManager...');
            window.authManager = new AuthManager();
            window.authManager.init();
            
        } catch (error) {
            console.error('❌ Falha crítica:', error);
            if (authLoading) authLoading.style.display = 'none';
            if (loginSection) loginSection.style.display = 'block';
            
            alert('Erro ao carregar o sistema. Recarregue a página.');
        }
    }, 500);
});

// Funções globais para templates
window.loginWithGoogle = () => window.authManager?.loginWithGoogle();
window.logout = () => {
    if (confirm('Tem certeza que deseja sair?')) {
        window.authManager?.logout();
    }
};
window.redirectToGame = () => window.authManager?.redirectToGame();