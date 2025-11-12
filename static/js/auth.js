// static/js/auth.js - VERSÃO CORRIGIDA E ALINHADA COM NOVO FLUXO
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.loginInProgress = false;
        this.syncInProgress = false;
        this.lastSync = 0;
        this.syncThrottle = 2000;
        
        console.log('🔄 AuthManager inicializando...');
        this.init();
    }

    async init() {
        try {
            // Primeiro: inicializar Firebase com configuração do backend
            await this.initializeFirebase();
            
            // Depois: configurar listeners e verificar auth
            this.setupAuthListeners();
            this.setupEventListeners();
            await this.checkInitialAuth();
            
            console.log('✅ AuthManager inicializado com Firebase');
        } catch (error) {
            console.error('❌ Falha na inicialização do AuthManager:', error);
            this.showCriticalError('Erro ao carregar sistema de autenticação');
        }
    }

    async initializeFirebase() {
        try {
            console.log('🔥 Inicializando Firebase...');
            
            // Verificar se Firebase está disponível globalmente
            if (typeof firebase === 'undefined') {
                throw new Error('Firebase não carregado');
            }

            // Obter configuração do backend
            const config = await this.getFirebaseConfig();
            
            if (!config) {
                throw new Error('Configuração do Firebase não disponível');
            }

            // Inicializar Firebase
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
            console.log('📡 Obtendo configuração do Firebase do backend...');
            
            const response = await fetch('/api/auth/firebase-config');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const config = await response.json();
            console.log('✅ Configuração do Firebase obtida do backend');
            return config;
            
        } catch (error) {
            console.error('❌ Erro ao obter configuração:', error);
            return null;
        }
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? `Logado: ${user.email}` : 'Deslogado');
            
            if (this.loginInProgress) {
                console.log('⏳ Login já em andamento, ignorando...');
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
        document.addEventListener('click', (e) => {
            const target = e.target;
            
            // Login com Google
            if (target.id === 'loginButton' || target.closest('#loginButton') || 
                target.classList.contains('google-login') || target.closest('.google-login')) {
                e.preventDefault();
                e.stopPropagation();
                this.loginWithGoogle();
            }
            
            // Logout
            if (target.id === 'logoutButton' || target.closest('#logoutButton') ||
                target.classList.contains('logout-btn') || target.closest('.logout-btn')) {
                e.preventDefault();
                e.stopPropagation();
                this.logout();
            }
            
            // Navegação para jogo (apenas quando logado)
            if ((target.id === 'play-button' || target.closest('#play-button')) && this.isAuthenticated) {
                e.preventDefault();
                this.redirectToGame();
            }
        });
    }

    async checkInitialAuth() {
        try {
            console.log("🔍 Verificando autenticação inicial...");
            
            // Verificar sessão no servidor primeiro
            const serverAuth = await this.checkServerAuth();
            
            if (!serverAuth) {
                await this.checkFirebaseAuth();
            }
            
        } catch (error) {
            console.error('❌ Erro na verificação inicial:', error);
            this.handleUserLogout();
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
                console.log("📡 Status do servidor:", data.authenticated);
                
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
                console.log("👤 Usuário autenticado no Firebase:", user.email);
                await this.handleUserLogin(user);
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
            
            console.log('🔐 INICIANDO LOGIN COM GOOGLE...');
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            provider.setCustomParameters({ prompt: 'select_account' });
            
            console.log('🪟 Abrindo popup do Google...');
            const result = await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google bem-sucedido!', result.user.email);
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM GOOGLE:', error);
            this.hideLoading();
            this.loginInProgress = false;
            
            if (error.code !== 'auth/popup-closed-by-user' && error.code !== 'auth/cancelled-popup-request') {
                this.showMessage('Erro no login com Google: ' + this.getErrorMessage(error), 'error');
            }
            throw error;
        }
    }

    async handleUserLogin(user) {
        if (this.loginInProgress && this.user?.uid === user.uid) {
            console.log('⏳ Login já processado para este usuário');
            return;
        }

        console.log('👤 Processando login do usuário:', user.email);
        this.user = user;
        this.loginInProgress = true;
        
        try {
            // Throttle de sincronização
            const now = Date.now();
            if (now - this.lastSync < this.syncThrottle) {
                console.log('⏳ Sincronização recente, aguardando...');
                await new Promise(resolve => setTimeout(resolve, this.syncThrottle - (now - this.lastSync)));
            }

            // Obter token atualizado
            const token = await user.getIdToken(true);
            console.log('✅ Token obtido, sincronizando com servidor...');
            
            // Sincronizar com servidor backend
            const syncResult = await this.syncWithServer(token);
            
            if (syncResult.success) {
                this.isAuthenticated = true;
                this.lastSync = Date.now();
                
                // ✅ CORREÇÃO: Atualizar UI com dados do servidor (incluindo picture)
                this.updateUI(syncResult.user);
                
                // Salvar dados localmente
                this.saveLocalData(syncResult.user);
                
                console.log('✅ Login sincronizado com servidor');
                
                // Mostrar mensagem apenas se não for um carregamento inicial
                if (!this.authChecked) {
                    this.showMessage('Login bem-sucedido!', 'success');
                }
                
                // ✅ CORREÇÃO: Redirecionar para PERFIL em vez de jogo
                this.handlePostLoginRedirect();
                
            } else {
                throw new Error(syncResult.error || 'Falha na sincronização');
            }
        } catch (error) {
            console.error('❌ Erro ao sincronizar com servidor:', error);
            this.handleAuthFallback(user, error);
        } finally {
            this.loginInProgress = false;
            this.hideLoading();
        }
    }

    saveLocalData(userData) {
        try {
            localStorage.setItem('popcoin_user', JSON.stringify(userData));
            localStorage.setItem('popcoin_last_login', new Date().toISOString());
            localStorage.setItem('popcoin_last_sync', Date.now().toString());
        } catch (error) {
            console.warn('⚠️ Erro ao salvar dados locais:', error);
        }
    }

    handleAuthFallback(user, error) {
        console.warn('🔄 Usando fallback de autenticação local...');
        this.showMessage('Erro de conexão. Continuando offline...', 'warning');
        
        this.isAuthenticated = true;
        this.updateUI(user);
        
        const fallbackUser = {
            uid: user.uid,
            email: user.email,
            name: user.displayName || 'Jogador',
            picture: user.photoURL || '/static/images/default-avatar.png'
        };
        
        this.saveLocalData(fallbackUser);
    }

    handlePostLoginRedirect() {
        if (this.redirecting) return;
        
        const currentPath = window.location.pathname;
        const allowedPaths = ['/', '/index.html', ''];
        
        // ✅ CORREÇÃO: Redirecionar para PERFIL em vez de jogo
        if (allowedPaths.includes(currentPath)) {
            console.log('➡️ Redirecionando para PERFIL...');
            this.redirecting = true;
            
            setTimeout(() => {
                window.location.href = '/profile';
            }, 800);
        } else {
            console.log('📍 Já está na página correta:', currentPath);
        }
    }

    redirectToGame() {
        if (this.redirecting) return;
        
        console.log('🎮 Redirecionando para jogo...');
        this.redirecting = true;
        
        setTimeout(() => {
            window.location.href = '/game';
        }, 300);
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
                body: JSON.stringify({ token: token })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('📨 Resposta do servidor:', result.success ? '✅' : '❌');
            return result;
            
        } catch (error) {
            console.error('❌ Erro na sincronização:', error);
            return {
                success: true,
                user: {
                    uid: this.user.uid,
                    email: this.user.email,
                    name: this.user.displayName || 'Jogador',
                    picture: this.user.photoURL || '/static/images/default-avatar.png'
                }
            };
        } finally {
            this.syncInProgress = false;
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout');
        
        if (!this.isAuthenticated && !this.user) {
            console.log('🔁 Logout já processado');
            return;
        }
        
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
            localStorage.removeItem('popcoin_last_login');
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
            console.warn('⚠️ Falha ao notificar servidor do logout:', error);
        }
    }

    async logout() {
        if (this.loginInProgress) {
            console.log('⏳ Operação em andamento, aguarde...');
            return;
        }

        try {
            console.log('🚪 Iniciando logout...');
            this.showLoading('Saindo...');
            
            await firebase.auth().signOut();
            this.handleUserLogout();
            
            this.showMessage('Logout realizado com sucesso!', 'success');
            console.log('✅ Logout completo realizado');
            
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            this.showMessage('Erro ao fazer logout', 'error');
            this.handleUserLogout();
        } finally {
            this.hideLoading();
        }
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para usuário:', user ? user.email : 'null');
        
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

        // Esconder loading
        if (elements.authLoading) {
            elements.authLoading.classList.add('hidden');
        }

        if (user) {
            // ✅ CORREÇÃO: Usar picture do servidor (com fallback)
            if (elements.userPic) {
                elements.userPic.src = user.picture || user.photoURL || '/static/images/default-avatar.png';
                elements.userPic.alt = `Foto de ${user.name || user.displayName || user.email}`;
                elements.userPic.onerror = () => {
                    elements.userPic.src = '/static/images/default-avatar.png';
                };
            }
            if (elements.userName) {
                elements.userName.textContent = user.name || user.displayName || user.email || 'Usuário';
            }
            if (elements.userInfo) elements.userInfo.classList.remove('hidden');
            if (elements.loginSection) elements.loginSection.classList.add('hidden');
            
            // Mostrar seções apropriadas
            if (elements.gameSection) elements.gameSection.classList.remove('hidden');
            if (elements.welcomeSection) elements.welcomeSection.classList.add('hidden');
            if (elements.profileSection) elements.profileSection.classList.remove('hidden');
            if (elements.playButton) elements.playButton.classList.remove('hidden');
        } else {
            // Usuário não logado
            if (elements.userInfo) elements.userInfo.classList.add('hidden');
            if (elements.loginSection) elements.loginSection.classList.remove('hidden');
            
            // Esconder seções do jogo
            if (elements.gameSection) elements.gameSection.classList.add('hidden');
            if (elements.welcomeSection) elements.welcomeSection.classList.remove('hidden');
            if (elements.profileSection) elements.profileSection.classList.add('hidden');
            if (elements.playButton) elements.playButton.classList.add('hidden');
        }
    }

    handlePostLogoutRedirect() {
        if (this.redirecting) return;
        
        const currentPath = window.location.pathname;
        const gamePaths = ['/game', '/profile'];
        
        if (gamePaths.includes(currentPath)) {
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
            loadingElement.classList.add('hidden');
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
                background: rgba(0,0,0,0.8);
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                font-size: 1.2rem;
                backdrop-filter: blur(5px);
            `;
            document.body.appendChild(loadingEl);
        }
        loadingEl.innerHTML = `
            <div style="text-align: center;">
                <div class="loading-spinner" style="width: 40px; height: 40px; border: 4px solid rgba(255,255,255,0.3); border-radius: 50%; border-top: 4px solid white; animation: spin 1s linear infinite; margin: 0 auto 1rem;"></div>
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
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `auth-message message-${type}`;
        messageDiv.textContent = message;
        messageContainer.appendChild(messageDiv);
        
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    if (messageDiv.parentNode) {
                        messageDiv.remove();
                    }
                }, 300);
            }
        }, 5000);
    }

    getErrorMessage(error) {
        const errorMessages = {
            'auth/invalid-email': 'E-mail inválido.',
            'auth/user-disabled': 'Esta conta foi desativada.',
            'auth/user-not-found': 'Usuário não encontrado.',
            'auth/wrong-password': 'Senha incorreta.',
            'auth/email-already-in-use': 'Este e-mail já está em uso.',
            'auth/weak-password': 'A senha é muito fraca. Use pelo menos 6 caracteres.',
            'auth/network-request-failed': 'Erro de conexão. Verifique sua internet.',
            'auth/too-many-requests': 'Muitas tentativas. Tente novamente mais tarde.',
            'auth/operation-not-allowed': 'Operação não permitida.',
            'auth/popup-closed-by-user': 'Login cancelado.',
            'auth/cancelled-popup-request': 'Login cancelado.',
            'auth/popup-blocked': 'Popup bloqueado. Permita popups para este site.'
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

// Inicialização global
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando AuthManager...');
    
    // Estado inicial da UI
    const loginSection = document.getElementById('login-section');
    const authLoading = document.getElementById('auth-loading');
    
    if (loginSection) loginSection.classList.add('hidden');
    if (authLoading) authLoading.classList.remove('hidden');
    
    // Inicialização com verificações de dependência
    setTimeout(() => {
        try {
            if (typeof firebase === 'undefined') {
                throw new Error('Firebase não carregado');
            }
            
            console.log('🎯 Criando AuthManager...');
            window.authManager = new AuthManager();
            console.log('✅ Sistema de autenticação inicializado!');
            
        } catch (error) {
            console.error('❌ Falha crítica na inicialização do AuthManager:', error);
            const authLoading = document.getElementById('auth-loading');
            const loginSection = document.getElementById('login-section');
            if (authLoading) authLoading.classList.add('hidden');
            if (loginSection) loginSection.classList.remove('hidden');
            
            const errorMsg = document.createElement('div');
            errorMsg.style.cssText = 'background: #f8d7da; color: #721c24; padding: 10px; margin: 10px; border-radius: 5px;';
            errorMsg.textContent = 'Erro ao carregar o sistema. Recarregue a página.';
            document.body.prepend(errorMsg);
        }
    }, 200);
});

// Funções globais para compatibilidade
window.loginWithGoogle = () => window.authManager?.loginWithGoogle();
window.logout = () => window.authManager && confirm('Tem certeza que deseja sair?') && window.authManager.logout();
window.redirectToGame = () => window.authManager?.redirectToGame();