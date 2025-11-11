// Gerenciamento de autenticação - VERSÃO SIMPLIFICADA E FUNCIONAL
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.setupAuthListeners();
        this.checkAuthStatus();
    }

    setupAuthListeners() {
        // Configurar observador de estado de autenticação do Firebase
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔥 Firebase auth state changed:', user ? user.email : 'null');
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
    }

    async handleUserLogin(user) {
        console.log('👤 Processando login do usuário:', user.email);
        this.user = user;
        
        try {
            // Obter token do Firebase
            const token = await user.getIdToken();
            console.log('🔐 Token obtido, enviando para servidor...');
            
            // Enviar token para o servidor
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token })
            });

            const result = await response.json();
            console.log('📡 Resposta do servidor:', result);
            
            if (result.success) {
                this.isAuthenticated = true;
                this.updateUI(user);
                
                // Salvar no localStorage para persistência
                localStorage.setItem('popcoin_user', JSON.stringify(result.user));
                localStorage.setItem('popcoin_last_login', new Date().toISOString());
                
                console.log('✅ Login sincronizado com servidor');
                
                // Redirecionar para o jogo após login bem-sucedido
                if (window.location.pathname === '/') {
                    console.log('➡️ Redirecionando para /game');
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                console.error('❌ Erro no servidor:', result.error);
                this.showMessage('Erro no servidor: ' + result.error, 'error');
                await this.logout();
            }
        } catch (error) {
            console.error('❌ Erro ao comunicar com servidor:', error);
            this.showMessage('Erro de conexão com o servidor', 'error');
            this.handleUserLogout();
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout');
        this.user = null;
        this.isAuthenticated = false;
        this.updateUI(null);
        
        // Limpar dados de persistência
        localStorage.removeItem('popcoin_user');
        localStorage.removeItem('popcoin_last_login');
        
        // Redirecionar para a página inicial se estiver no jogo
        if (window.location.pathname === '/game') {
            console.log('⬅️ Redirecionando para /');
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        }
    }

    async loginWithGoogle() {
        try {
            console.log('🔐 Iniciando login com Google...');
            
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            // Forçar seleção de conta
            provider.setCustomParameters({
                prompt: 'select_account'
            });
            
            const result = await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google bem-sucedido');
            return result.user;
        } catch (error) {
            console.error('❌ Erro no login com Google:', error);
            
            let errorMessage = 'Erro no login: ';
            switch (error.code) {
                case 'auth/popup-blocked':
                    errorMessage += 'Popup bloqueado. Permita popups para este site.';
                    break;
                case 'auth/popup-closed-by-user':
                    errorMessage += 'Popup fechado pelo usuário.';
                    break;
                case 'auth/unauthorized-domain':
                    errorMessage += 'Domínio não autorizado.';
                    break;
                case 'auth/network-request-failed':
                    errorMessage += 'Erro de rede. Verifique sua conexão.';
                    break;
                default:
                    errorMessage += error.message;
            }
            
            this.showMessage(errorMessage, 'error');
            throw error;
        }
    }

    async logout() {
        try {
            console.log('🚪 Iniciando logout...');
            
            // Fazer logout no Firebase primeiro
            await firebase.auth().signOut();
            
            // Fazer logout no servidor
            await fetch('/api/auth/logout', { method: 'POST' });
            
            this.handleUserLogout();
            console.log('✅ Logout completo realizado');
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            // Mesmo com erro, tentar limpar o estado local
            this.handleUserLogout();
        }
    }

    async checkAuthStatus() {
        try {
            console.log("🔍 Verificando status de autenticação...");
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            
            console.log("📡 Status da autenticação:", data.authenticated);

            if (data.authenticated) {
                this.isAuthenticated = true;
                this.user = data.user;
                this.updateUI(this.user);
                
                // Se estiver na página inicial e autenticado, redirecionar
                if (window.location.pathname === '/' && !this.redirecting) {
                    console.log("➡️ Usuário autenticado na página inicial, redirecionando...");
                    this.redirecting = true;
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                this.isAuthenticated = false;
                // Se estiver na página do jogo e não autenticado, redirecionar
                if (window.location.pathname === '/game' && !this.redirecting) {
                    console.log("⬅️ Usuário não autenticado no jogo, redirecionando...");
                    this.redirecting = true;
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                }
            }
        } catch (error) {
            console.error('❌ Erro ao verificar status:', error);
        } finally {
            this.authChecked = true;
            this.hideAuthLoading();
        }
    }

    updateUI(user) {
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');

        if (user) {
            // Usuário logado
            if (user.photoURL) {
                userPic.src = user.photoURL;
                userPic.style.display = 'inline';
            }
            userName.textContent = user.displayName || user.email || 'Usuário';
            if (userInfo) userInfo.style.display = 'flex';
            if (loginSection) loginSection.style.display = 'none';
        } else {
            // Usuário não logado
            if (userInfo) userInfo.style.display = 'none';
            if (loginSection) loginSection.style.display = 'block';
        }
    }

    hideAuthLoading() {
        const loadingElement = document.getElementById('auth-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }

    showMessage(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
        // Sistema de mensagens simples - pode ser melhorado
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#ff4444' : '#44ff44'};
            color: white;
            border-radius: 5px;
            z-index: 10000;
            font-weight: bold;
        `;
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            document.body.removeChild(messageDiv);
        }, 5000);
    }
}

// Inicialização global
let authManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando sistema de autenticação...');
    
    // Mostrar loading
    const loadingElement = document.getElementById('auth-loading');
    if (loadingElement) {
        loadingElement.style.display = 'flex';
    }
    
    // Aguardar o Firebase carregar
    setTimeout(() => {
        authManager = new AuthManager();
        window.authManager = authManager;
        
        // Configurar event listeners para botões
        const loginButton = document.getElementById('loginButton');
        const logoutButton = document.getElementById('logoutButton');

        if (loginButton) {
            loginButton.addEventListener('click', () => authManager.loginWithGoogle());
        }

        if (logoutButton) {
            logoutButton.addEventListener('click', () => {
                if (confirm('Tem certeza que deseja sair?')) {
                    authManager.logout();
                }
            });
        }
    }, 500);
});

// Funções globais para compatibilidade com HTML onclick
window.loginWithGoogle = () => {
    if (window.authManager) {
        window.authManager.loginWithGoogle();
    } else {
        console.error('AuthManager não inicializado');
    }
};

window.logout = () => {
    if (window.authManager) {
        if (confirm('Tem certeza que deseja sair?')) {
            window.authManager.logout();
        }
    } else {
        console.error('AuthManager não inicializado');
    }
};