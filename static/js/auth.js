// static/js/auth.js - VERSÃO CORRIGIDA
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.loginInProgress = false;
        
        console.log('🔄 AuthManager inicializando...');
    }

    async init() {
        if (this.initialized) {
            console.log('✅ AuthManager já inicializado');
            return;
        }

        try {
            // ✅ CORREÇÃO: Usar configuração já inicializada no base.html
            console.log('🔥 Firebase já inicializado no base.html');
            this.setupAuthListeners();
            this.setupEventListeners();
            await this.checkInitialAuth();
            
            this.initialized = true;
            console.log('✅ AuthManager inicializado com sucesso');
        } catch (error) {
            console.error('❌ Falha na inicialização do AuthManager:', error);
            this.showMessage('Erro ao carregar sistema de autenticação', 'error');
        }
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        // ✅ CORREÇÃO: Listener simplificado
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? user.email : 'Deslogado');
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
    }

    setupEventListeners() {
        // ✅ CORREÇÃO: Listeners simplificados
        document.addEventListener('click', (e) => {
            if (e.target.id === 'logoutButton' || e.target.closest('#logoutButton')) {
                e.preventDefault();
                this.logout();
            }
        });
    }

    async checkInitialAuth() {
        try {
            console.log("🔍 Verificando autenticação inicial...");
            await this.checkServerAuth();
        } catch (error) {
            console.error('❌ Erro na verificação inicial:', error);
        } finally {
            this.authChecked = true;
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

    async loginWithGoogle() {
        if (this.loginInProgress) {
            console.log('⏳ Login já em andamento...');
            return;
        }

        try {
            console.log('🔐 Iniciando login com Google...');
            this.loginInProgress = true;
            
            // ✅ CORREÇÃO: Mostrar loading global
            if (window.showGlobalLoading) {
                window.showGlobalLoading('Conectando com Google...');
            }
            
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            // ✅ CORREÇÃO: Timeout para detectar popup bloqueado
            const popupTimeout = setTimeout(() => {
                console.log('⚠️ Verificando popup...');
            }, 2000);
            
            const result = await firebase.auth().signInWithPopup(provider);
            clearTimeout(popupTimeout);
            
            console.log('✅ Login com Google bem-sucedido:', result.user.email);
            
        } catch (error) {
            console.error('❌ Erro no login com Google:', error);
            this.loginInProgress = false;
            
            // ✅ CORREÇÃO: Esconder loading em caso de erro
            if (window.hideGlobalLoading) {
                window.hideGlobalLoading();
            }
            
            if (error.code === 'auth/popup-blocked') {
                this.showMessage('Popup bloqueado! Permita popups para este site.', 'error');
            } else if (error.code === 'auth/popup-closed-by-user') {
                console.log('ℹ️ Popup fechado pelo usuário');
            } else {
                this.showMessage('Erro no login: ' + this.getErrorMessage(error), 'error');
            }
        }
    }

    async handleUserLogin(user) {
        console.log('👤 Processando login:', user.email);
        this.user = user;
        
        try {
            // ✅ CORREÇÃO: Obter token e sincronizar
            const token = await user.getIdToken();
            console.log('✅ Token obtido, sincronizando...');
            
            const syncResult = await this.syncWithServer(token);
            
            if (syncResult.success) {
                this.isAuthenticated = true;
                this.updateUI(syncResult.user);
                this.saveLocalData(syncResult.user);
                
                console.log('✅ Login sincronizado com servidor');
                this.showMessage('Login bem-sucedido!', 'success');
                
                // ✅ CORREÇÃO: Redirecionar para perfil
                this.handlePostLoginRedirect();
                
            } else {
                throw new Error(syncResult.error || 'Falha na sincronização');
            }
        } catch (error) {
            console.error('❌ Erro ao sincronizar:', error);
            await firebase.auth().signOut();
            this.showMessage('Erro ao conectar com servidor', 'error');
        } finally {
            this.loginInProgress = false;
            if (window.hideGlobalLoading) {
                window.hideGlobalLoading();
            }
        }
    }

    async syncWithServer(token) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ token })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('❌ Erro na sincronização:', error);
            return {
                success: false,
                error: error.message
            };
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
        this.showMessage('Logout realizado!', 'success');
    }

    clearLocalData() {
        try {
            localStorage.removeItem('popcoin_user');
            localStorage.removeItem('popcoin_last_sync');
        } catch (error) {
            console.warn('⚠️ Erro ao limpar dados locais:', error);
        }
    }

    async logout() {
        try {
            console.log('🚪 Iniciando logout...');
            
            await firebase.auth().signOut();
            this.handleUserLogout();
            
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            this.showMessage('Erro ao fazer logout', 'error');
        }
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para:', user ? user.email : 'null');
        
        // Disparar evento para outros componentes
        const event = new CustomEvent('authStateChanged', {
            detail: { isAuthenticated: !!user, user: user }
        });
        window.dispatchEvent(event);
        
        // ✅ CORREÇÃO: Atualizar elementos específicos
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');
        
        if (user) {
            if (userPic) {
                userPic.src = user.picture || user.photoURL || '/static/images/default-avatar.png';
                userPic.onerror = () => {
                    userPic.src = '/static/images/default-avatar.png';
                };
            }
            if (userName) {
                userName.textContent = user.name || user.displayName || user.email || 'Usuário';
            }
            
            this.toggleElement(userInfo, true);
            this.toggleElement(loginSection, false);
        } else {
            this.toggleElement(userInfo, false);
            this.toggleElement(loginSection, true);
        }
    }

    toggleElement(element, show) {
        if (!element) return;
        
        if (show) {
            element.classList.remove('hidden');
        } else {
            element.classList.add('hidden');
        }
    }

    handlePostLoginRedirect() {
        const currentPath = window.location.pathname;
        
        // ✅ CORREÇÃO: Redirecionar apenas se estiver na página inicial
        if (currentPath === '/' || currentPath === '/index.html') {
            console.log('➡️ Redirecionando para perfil...');
            
            setTimeout(() => {
                window.location.href = '/profile';
            }, 1500);
        }
    }

    showMessage(message, type = 'info') {
        console.log(`💬 ${type.toUpperCase()}: ${message}`);
        
        // Usar alert simples por enquanto
        if (type === 'error') {
            alert(`❌ ${message}`);
        } else {
            alert(`✅ ${message}`);
        }
    }

    getErrorMessage(error) {
        const errorMessages = {
            'auth/popup-blocked': 'Popup bloqueado. Permita popups para este site.',
            'auth/popup-closed-by-user': 'Login cancelado.',
            'auth/network-request-failed': 'Erro de conexão. Verifique sua internet.',
            'auth/unauthorized-domain': 'Domínio não autorizado. Contate o suporte.',
        };

        return errorMessages[error.code] || error.message;
    }
}

// ✅ CORREÇÃO: Inicialização simplificada
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, preparando AuthManager...');
    
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
            alert('Erro ao carregar o sistema. Recarregue a página.');
        }
    }, 100);
});

// Funções globais
window.loginWithGoogle = () => window.authManager?.loginWithGoogle();
window.logout = () => {
    if (confirm('Tem certeza que deseja sair?')) {
        window.authManager?.logout();
    }
};