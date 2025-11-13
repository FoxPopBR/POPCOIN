// static/js/auth.js - VERSÃO CORRIGIDA E SIMPLIFICADA
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.initialized = false;
        this.authChecked = false;
        
        console.log('🔄 AuthManager inicializando...');
    }

    async init() {
        if (this.initialized) return;

        try {
            console.log('🔥 Configurando AuthManager...');
            this.setupAuthListeners();
            this.setupEventListeners();
            
            // ✅ VERIFICAÇÃO ÚNICA - não fazer verificação constante
            await this.checkInitialAuth();
            this.authChecked = true;
            
            this.initialized = true;
            console.log('✅ AuthManager inicializado com sucesso');
        } catch (error) {
            console.error('❌ Falha na inicialização:', error);
            this.authChecked = true; // Marcar como verificado mesmo em caso de erro
        }
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        // ✅ LISTENER SIMPLIFICADO - sem lógica complexa
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? user.email : 'Deslogado');
            
            if (user && !this.isAuthenticated) {
                await this.handleUserLogin(user);
            } else if (!user && this.isAuthenticated) {
                this.handleUserLogout();
            }
        });
    }

    setupEventListeners() {
        // ✅ APENAS LOGOUT - login é feito pelos botões nas páginas
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
            const response = await fetch('/api/auth/status');
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.authenticated && data.user) {
                    console.log("✅ Sessão encontrada:", data.user.email);
                    this.user = data.user;
                    this.isAuthenticated = true;
                    this.updateUI(this.user);
                    return true;
                }
            }
            
            console.log("🔐 Nenhuma sessão ativa");
            return false;
            
        } catch (error) {
            console.error('❌ Erro na verificação inicial:', error);
            return false;
        }
    }

    async loginWithGoogle() {
        try {
            console.log('🔐 Iniciando login com Google...');
            
            if (window.showGlobalLoading) {
                window.showGlobalLoading('Conectando com Google...');
            }
            
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google iniciado');
            
        } catch (error) {
            console.error('❌ Erro no login com Google:', error);
            
            if (window.hideGlobalLoading) {
                window.hideGlobalLoading();
            }
            
            if (error.code === 'auth/popup-blocked') {
                alert('Popup bloqueado! Permita popups para este site.');
            } else if (error.code !== 'auth/popup-closed-by-user') {
                alert('Erro no login: ' + this.getErrorMessage(error));
            }
        }
    }

    async handleUserLogin(user) {
        console.log('👤 Processando login:', user.email);
        
        try {
            const token = await user.getIdToken();
            console.log('✅ Token obtido, sincronizando...');
            
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.user = result.user;
                this.isAuthenticated = true;
                this.updateUI(this.user);
                
                console.log('✅ Login sincronizado com servidor');
                
                // ✅ REDIRECIONAMENTO INTELIGENTE
                this.handlePostLoginRedirect();
                
            } else {
                throw new Error(result.error || 'Falha na sincronização');
            }
        } catch (error) {
            console.error('❌ Erro ao sincronizar:', error);
            await firebase.auth().signOut();
            alert('Erro ao conectar com servidor');
        } finally {
            if (window.hideGlobalLoading) {
                window.hideGlobalLoading();
            }
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout no frontend');
        
        this.user = null;
        this.isAuthenticated = false;
        this.updateUI(null);
    }

    async logout() {
        try {
            console.log('🚪 Iniciando logout completo...');
            
            // ✅ 1. Fazer logout no Firebase
            await firebase.auth().signOut();
            
            // ✅ 2. Fazer logout no servidor
            await fetch('/api/auth/logout', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            // ✅ 3. Limpar estado local
            this.handleUserLogout();
            
            console.log('✅ Logout completo realizado');
            
            // ✅ 4. Redirecionar para home
            window.location.href = '/';
            
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            // Mesmo com erro, limpar estado local
            this.handleUserLogout();
            window.location.href = '/';
        }
    }

    // ✅ MÉTODOS NOVOS ADICIONADOS PARA CORRIGIR O ERRO
    isUserAuthenticated() {
        return this.isAuthenticated && this.user !== null;
    }

    getAuthState() {
        return {
            isAuthenticated: this.isAuthenticated,
            user: this.user,
            authChecked: this.authChecked
        };
    }

    isAuthChecked() {
        return this.authChecked;
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para:', user ? user.email : 'null');
        
        // ✅ EVENTO PARA ATUALIZAR OUTROS COMPONENTES
        const event = new CustomEvent('authStateChanged', {
            detail: { 
                isAuthenticated: !!user, 
                user: user 
            }
        });
        window.dispatchEvent(event);
        
        // ✅ ATUALIZAR ELEMENTOS DA UI
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');
        
        if (user) {
            // ✅ AVATAR COM FALLBACK ROBUSTO
            if (userPic) {
                const avatarUrl = user.picture || user.photoURL || '/static/images/default-avatar.png';
                console.log('🖼️ Tentando carregar avatar:', avatarUrl);
                
                userPic.src = avatarUrl;
                userPic.onerror = function() {
                    console.log('❌ Erro ao carregar avatar, usando fallback');
                    this.src = '/static/images/default-avatar.png';
                    this.onerror = null; // Prevenir loop
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
        element.classList.toggle('hidden', !show);
    }

    handlePostLoginRedirect() {
        const currentPath = window.location.pathname;
        console.log('➡️ Verificando redirecionamento para:', currentPath);
        
        // ✅ REDIRECIONAR APENAS SE ESTIVER NA HOME
        if (currentPath === '/' || currentPath === '/index.html') {
            console.log('➡️ Redirecionando para perfil...');
            setTimeout(() => {
                window.location.href = '/profile';
            }, 1000);
        }
    }

    getErrorMessage(error) {
        const errorMessages = {
            'auth/popup-blocked': 'Popup bloqueado. Permita popups para este site.',
            'auth/popup-closed-by-user': 'Login cancelado.',
            'auth/network-request-failed': 'Erro de conexão. Verifique sua internet.',
        };
        return errorMessages[error.code] || error.message;
    }
}

// ✅ INICIALIZAÇÃO SIMPLES
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando AuthManager...');
    
    setTimeout(() => {
        if (typeof firebase !== 'undefined') {
            window.authManager = new AuthManager();
            window.authManager.init();
        } else {
            console.error('❌ Firebase não carregado');
        }
    }, 500);
});

// ✅ FUNÇÕES GLOBAIS
window.handleGlobalLogin = () => window.authManager?.loginWithGoogle();
window.logout = () => {
    if (confirm('Tem certeza que deseja sair?')) {
        window.authManager?.logout();
    }
};