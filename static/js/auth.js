// Gerenciamento de autenticação - VERSÃO COMPLETA
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.initFirebase();
        this.checkPersistentAuth();
    }

    initFirebase() {
        // Configuração do Firebase será injetada pelo template
        console.log('🔥 Firebase inicializado');
        
        // Configurar observador de estado de autenticação
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔥 Estado de autenticação alterado:', user ? user.email : 'null');
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
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

    async handleUserLogin(user) {
        console.log('👤 Processando login do usuário:', user.email);
        this.user = user;
        
        try {
            // Obter token do Firebase
            const token = await user.getIdToken();
            
            // Enviar token para o servidor
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token })
            });

            const result = await response.json();
            
            if (result.success) {
                this.isAuthenticated = true;
                this.updateUI(user);
                
                // Salvar no localStorage para persistência
                localStorage.setItem('popcoin_user', JSON.stringify(result.user));
                localStorage.setItem('popcoin_last_login', new Date().toISOString());
                
                console.log('✅ Login sincronizado com servidor');
                await this.syncWithBackend();
            } else {
                console.error('❌ Erro no servidor:', result.error);
                await this.logout();
            }
        } catch (error) {
            console.error('❌ Erro ao comunicar com servidor:', error);
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
    }

    async logout() {
        try {
            console.log('🚪 Iniciando logout...');
            
            // Fazer logout no Firebase primeiro
            await firebase.auth().signOut();
            
            // Fazer logout no servidor
            await fetch('/api/auth/logout', { method: 'POST' });
            
            this.handleUserLogout();
            await this.syncWithBackend();
            console.log('✅ Logout completo realizado');
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            // Mesmo com erro, tentar limpar o estado local
            this.handleUserLogout();
            await this.syncWithBackend();
        }
    }

    async syncWithBackend() {
        try {
            console.log("🔄 Sincronizando com backend...");
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            
            console.log("📡 Status da autenticação:", data.authenticated);
            console.log("📍 Página atual:", window.location.pathname);

            if (data.authenticated) {
                this.isAuthenticated = true;
                // Só redireciona se estiver na página inicial E não estiver já redirecionando
                if (window.location.pathname === '/' && !this.redirecting) {
                    console.log("➡️ Redirecionando para /game");
                    this.redirecting = true;
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                this.isAuthenticated = false;
                // Só redireciona se estiver na página do jogo E não estiver já redirecionando
                if (window.location.pathname === '/game' && !this.redirecting) {
                    console.log("⬅️ Redirecionando para /");
                    this.redirecting = true;
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 1000);
                }
            }
        } catch (error) {
            console.error('❌ Erro na sincronização:', error);
        } finally {
            this.authChecked = true;
            // Reset da flag de redirecionamento após um tempo
            setTimeout(() => {
                this.redirecting = false;
            }, 2000);
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
            } else {
                userPic.style.display = 'none';
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

    async checkPersistentAuth() {
        try {
            const savedUser = localStorage.getItem('popcoin_user');
            if (savedUser) {
                console.log("📱 Usuário encontrado no localStorage");
                this.user = JSON.parse(savedUser);
                this.isAuthenticated = true;
                await this.syncWithBackend();
            } else {
                console.log("📱 Nenhum usuário no localStorage");
                await this.syncWithBackend();
            }
        } catch (error) {
            console.error('❌ Erro na verificação persistente:', error);
            this.authChecked = true;
        }
    }

    showMessage(message, type = 'info') {
        // Implementação simples de sistema de mensagens
        console.log(`${type.toUpperCase()}: ${message}`);
        alert(message); // Temporário - pode ser substituído por um sistema mais sofisticado
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
    
    // Aguardar um pouco para garantir que o Firebase está carregado
    setTimeout(() => {
        authManager = new AuthManager();
        window.authManager = authManager;

        // Configurar event listeners
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
        
        // Esconder loading após verificação
        setTimeout(() => {
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }
        }, 2000);
        
    }, 100);
});

// Funções globais para compatibilidade
window.loginWithGoogle = () => {
    if (window.authManager) {
        window.authManager.loginWithGoogle();
    }
};

window.logout = () => {
    if (window.authManager && confirm('Tem certeza que deseja sair?')) {
        window.authManager.logout();
    }
};