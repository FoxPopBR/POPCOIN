// static/js/auth.js - VERSÃO OTIMIZADA E CORRIGIDA
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.loginInProgress = false;
        this.syncInProgress = false;
        this.lastSync = 0;
        this.syncThrottle = 2000; // 2 segundos entre sincronizações
        
        console.log('🔄 AuthManager inicializando...');
        this.init();
    }

    init() {
        this.setupAuthListeners();
        this.setupEventListeners();
        this.checkInitialAuth();
        console.log('✅ AuthManager inicializado');
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? `Logado: ${user.email}` : 'Deslogado');
            
            // Evitar processamento duplicado
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
        // Event listeners para botões existentes - com prevenção de duplo clique
        document.addEventListener('click', (e) => {
            // Login com Google
            if (e.target.id === 'loginButton' || e.target.closest('#loginButton')) {
                e.preventDefault();
                e.stopPropagation();
                this.loginWithGoogle();
            }
            // Logout
            if (e.target.id === 'logoutButton' || e.target.closest('#logoutButton')) {
                e.preventDefault();
                e.stopPropagation();
                this.logout();
            }
        });

        // Delegation para elementos dinâmicos
        document.addEventListener('click', (e) => {
            const target = e.target;
            
            if (target.classList.contains('google-login') || target.closest('.google-login')) {
                e.preventDefault();
                this.loginWithGoogle();
            }
            
            if (target.classList.contains('email-login') || target.closest('.email-login')) {
                e.preventDefault();
                this.loginWithEmail();
            }
            
            if (target.classList.contains('email-register') || target.closest('.email-register')) {
                e.preventDefault();
                this.registerWithEmail();
            }
            
            if (target.classList.contains('logout-btn') || target.closest('.logout-btn')) {
                e.preventDefault();
                this.logout();
            }
        });
    }

    async checkInitialAuth() {
        try {
            console.log("🔍 Verificando autenticação inicial...");
            
            // Primeiro verificar sessão no servidor (mais confiável)
            await this.checkServerAuth();
            
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
            
            // Nenhuma sessão ativa no servidor, verificar Firebase como fallback
            return await this.checkFirebaseAuth();
            
        } catch (error) {
            console.error('❌ Erro ao verificar sessão:', error);
            return await this.checkFirebaseAuth();
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
            
            // O onAuthStateChanged vai chamar handleUserLogin automaticamente
            
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
        // Prevenir múltiplas execuções simultâneas
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
                
                // Atualizar UI primeiro
                this.updateUI(user);
                
                // Salvar dados localmente
                localStorage.setItem('popcoin_user', JSON.stringify(syncResult.user));
                localStorage.setItem('popcoin_last_login', new Date().toISOString());
                
                console.log('✅ Login sincronizado com servidor');
                
                // Mostrar mensagem apenas se não for um carregamento inicial
                if (!this.authChecked) {
                    this.showMessage('Login bem-sucedido!', 'success');
                }
                
                // Redirecionar apenas se necessário
                this.handlePostLoginRedirect();
                
            } else {
                throw new Error(syncResult.error || 'Falha na sincronização');
            }
        } catch (error) {
            console.error('❌ Erro ao sincronizar com servidor:', error);
            
            // Fallback: continuar com autenticação local
            this.showMessage('Erro de conexão. Continuando offline...', 'warning');
            this.isAuthenticated = true;
            this.updateUI(user);
            localStorage.setItem('popcoin_user', JSON.stringify({
                uid: user.uid,
                email: user.email,
                name: user.displayName || 'Jogador'
            }));
        } finally {
            this.loginInProgress = false;
            this.hideLoading();
        }
    }

    handlePostLoginRedirect() {
        // Evitar redirecionamentos múltiplos
        if (this.redirecting) return;
        
        const currentPath = window.location.pathname;
        
        // Só redirecionar se estiver na página inicial
        if (currentPath === '/' || currentPath === '/index.html') {
            console.log('➡️ Redirecionando para jogo...');
            this.redirecting = true;
            
            // Pequeno delay para garantir que a UI foi atualizada
            setTimeout(() => {
                window.location.href = '/game';
            }, 800);
        } else {
            console.log('📍 Já está na página correta:', currentPath);
        }
    }

    handlePostLogoutRedirect() {
        if (this.redirecting) return;
        
        const currentPath = window.location.pathname;
        
        // Só redirecionar se estiver na página do jogo ou perfil
        if (currentPath === '/game' || currentPath === '/profile') {
            console.log('⬅️ Redirecionando para página inicial...');
            this.redirecting = true;
            
            setTimeout(() => {
                window.location.href = '/';
            }, 800);
        }
    }

    async syncWithServer(token) {
        // Prevenir múltiplas sincronizações simultâneas
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
            // Fallback: retornar autenticação básica
            return {
                success: true,
                user: {
                    uid: this.user.uid,
                    email: this.user.email,
                    name: this.user.displayName || 'Jogador'
                }
            };
        } finally {
            this.syncInProgress = false;
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout');
        
        // Prevenir múltiplos logouts
        if (!this.isAuthenticated && !this.user) {
            console.log('🔁 Logout já processado');
            return;
        }
        
        this.user = null;
        this.isAuthenticated = false;
        this.updateUI(null);
        
        // Limpar dados locais
        localStorage.removeItem('popcoin_user');
        localStorage.removeItem('popcoin_last_login');
        
        // Notificar servidor do logout (não bloquear)
        this.notifyServerLogout();
        
        // Redirecionar se necessário
        this.handlePostLogoutRedirect();
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
            // Forçar logout mesmo com erro
            this.handleUserLogout();
        } finally {
            this.hideLoading();
        }
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para usuário:', user ? user.email : 'null');
        
        // Elementos comuns
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');
        const authLoading = document.getElementById('auth-loading');
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');

        // Esconder loading de auth
        if (authLoading) {
            authLoading.classList.add('hidden');
        }

        if (user) {
            // Usuário logado
            if (userPic) {
                userPic.src = user.photoURL || '/static/images/default-avatar.png';
                userPic.alt = `Foto de ${user.displayName || user.email}`;
                userPic.onerror = () => {
                    userPic.src = '/static/images/default-avatar.png';
                };
            }
            if (userName) {
                userName.textContent = user.displayName || user.email || 'Usuário';
            }
            if (userInfo) userInfo.classList.remove('hidden');
            if (loginSection) loginSection.classList.add('hidden');
        } else {
            // Usuário não logado
            if (userInfo) userInfo.classList.add('hidden');
            if (loginSection) loginSection.classList.remove('hidden');
        }

        // Atualizar seções específicas da página
        this.updatePageSections();
    }

    updatePageSections() {
        const gameSection = document.getElementById('game-section');
        const welcomeSection = document.getElementById('welcome-section');
        const profileSection = document.getElementById('profile-section');
        
        if (this.isAuthenticated) {
            if (gameSection) gameSection.classList.remove('hidden');
            if (welcomeSection) welcomeSection.classList.add('hidden');
            if (profileSection) profileSection.classList.remove('hidden');
        } else {
            if (gameSection) gameSection.classList.add('hidden');
            if (welcomeSection) welcomeSection.classList.remove('hidden');
            if (profileSection) profileSection.classList.add('hidden');
        }
    }

    // ... (os métodos restantes permanecem iguais: showLoading, hideLoading, showMessage, etc.)
    // Manter os mesmos métodos auxiliares da versão anterior
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
            'auth/cancelled-popup-request': 'Login cancelado.'
        };

        return errorMessages[error.code] || `Erro: ${error.message}`;
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    getCurrentUser() {
        return this.user;
    }

    isUserAuthenticated() {
        return this.isAuthenticated;
    }

    async refreshToken() {
        if (this.user) {
            return await this.user.getIdToken(true);
        }
        return null;
    }
}

// Inicialização global
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando AuthManager...');
    
    // Configurar estado inicial da UI
    const loginSection = document.getElementById('login-section');
    const authLoading = document.getElementById('auth-loading');
    
    if (loginSection) loginSection.classList.add('hidden');
    if (authLoading) authLoading.classList.remove('hidden');
    
    // Inicializar AuthManager
    setTimeout(() => {
        try {
            console.log('🎯 Criando AuthManager...');
            window.authManager = new AuthManager();
            console.log('✅ Sistema de autenticação inicializado!');
        } catch (error) {
            console.error('❌ Falha crítica na inicialização do AuthManager:', error);
            const authLoading = document.getElementById('auth-loading');
            const loginSection = document.getElementById('login-section');
            if (authLoading) authLoading.classList.add('hidden');
            if (loginSection) loginSection.classList.remove('hidden');
        }
    }, 100);
});

// Manter funções globais para compatibilidade
window.loginWithGoogle = function() {
    if (window.authManager) {
        window.authManager.loginWithGoogle();
    }
};

window.loginWithEmail = function() {
    if (window.authManager) {
        window.authManager.loginWithEmail();
    }
};

window.registerWithEmail = function() {
    if (window.authManager) {
        window.authManager.registerWithEmail();
    }
};

window.resetPassword = function() {
    if (window.authManager) {
        window.authManager.resetPassword();
    }
};

window.logout = function() {
    if (window.authManager && confirm('Tem certeza que deseja sair?')) {
        window.authManager.logout();
    }
};