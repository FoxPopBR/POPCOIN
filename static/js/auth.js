// Gerenciamento de autenticação
class AuthManager {
    constructor() {
        this.user = null;
        this.authChecked = false;
        this.initFirebase();
        this.setupAuthListeners();
    }

    initFirebase() {
        console.log('Firebase configurado');
    }

    setupAuthListeners() {
        // Observar mudanças no estado de autenticação do Firebase
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('Firebase auth state changed:', user);
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
            
            this.authChecked = true;
        });
    }

    async handleUserLogin(user) {
        console.log('Processando login do usuário:', user.email);
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
                this.updateUI(user);
                // Salvar estado de login no localStorage para persistência
                localStorage.setItem('firebase_uid', user.uid);
                localStorage.setItem('last_login', new Date().toISOString());
                console.log('✅ Login sincronizado com servidor');
                
                // Redirecionar apenas se estiver na página inicial
                if (window.location.pathname === '/') {
                    console.log('Redirecionando para /game');
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                console.error('❌ Erro no servidor:', result.error);
                // Se o servidor rejeitou, fazer logout no Firebase também
                await this.logout();
            }
        } catch (error) {
            console.error('❌ Erro ao comunicar com servidor:', error);
            this.handleUserLogout();
        }
    }

    handleUserLogout() {
        console.log('Processando logout');
        this.user = null;
        this.updateUI(null);
        // Limpar dados de persistência
        localStorage.removeItem('firebase_uid');
        localStorage.removeItem('last_login');
        
        // Se estiver na página do jogo, redirecionar para início
        if (window.location.pathname === '/game') {
            console.log('Redirecionando para /');
            setTimeout(() => {
                window.location.href = '/';
            }, 500);
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
            userInfo.style.display = 'flex';
            loginSection.style.display = 'none';
        } else {
            // Usuário não logado
            userInfo.style.display = 'none';
            loginSection.style.display = 'block';
        }
    }

    // Login com Google
    async loginWithGoogle() {
        try {
            console.log('Iniciando login com Google...');
            
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
            
            alert(errorMessage);
            throw error;
        }
    }

    // Logout
    async logout() {
        try {
            console.log('Iniciando logout...');
            
            // Fazer logout no Firebase primeiro
            await firebase.auth().signOut();
            
            // Fazer logout no servidor
            await fetch('/api/auth/logout');
            
            this.handleUserLogout();
            console.log('✅ Logout completo realizado');
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            // Mesmo com erro, tentar limpar o estado local
            this.handleUserLogout();
        }
    }

    // Verificar status de autenticação
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('❌ Erro ao verificar status:', error);
            return { authenticated: false, user: null };
        }
    }

    // Verificar login persistente
    checkPersistentAuth() {
        const savedUID = localStorage.getItem('firebase_uid');
        const lastLogin = localStorage.getItem('last_login');
        
        if (savedUID && lastLogin) {
            const loginTime = new Date(lastLogin);
            const now = new Date();
            const hoursDiff = (now - loginTime) / (1000 * 60 * 60);
            
            // Se fez login nas últimas 24 horas, considerar como "lembrado"
            if (hoursDiff < 24) {
                return true;
            }
        }
        
        return false;
    }

    // Verificar se há usuário salvo e tentar recuperar sessão
    async tryRestoreSession() {
        if (this.checkPersistentAuth()) {
            console.log('Tentando restaurar sessão persistente...');
            // Aguardar o Firebase verificar se ainda está autenticado
            // O listener onAuthStateChanged irá tratar o resto
        }
    }
}

// Instância global do gerenciador de autenticação
const authManager = new AuthManager();

// Funções globais para os botões HTML
window.loginWithGoogle = () => {
    console.log('Botão login clicado');
    authManager.loginWithGoogle();
};

window.logout = () => {
    console.log('Botão logout clicado');
    if (confirm('Tem certeza que deseja sair?')) {
        authManager.logout();
    }
};

// Verificação inicial de autenticação
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Página carregada, aguardando verificação de autenticação...');
    
    // Mostrar loading se o elemento existir
    const loadingElement = document.getElementById('auth-loading');
    if (loadingElement) {
        loadingElement.style.display = 'flex';
    }
    
    // Aguardar a verificação inicial do Firebase
    const waitForAuthCheck = () => {
        return new Promise((resolve) => {
            const check = () => {
                if (authManager.authChecked) {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    };
    
    await waitForAuthCheck();
    
    // Agora verificar o status com o servidor
    const authStatus = await authManager.checkAuthStatus();
    console.log('Status final de autenticação:', authStatus);
    
    // Lógica de redirecionamento mais conservadora
    if (authStatus.authenticated && window.location.pathname === '/') {
        console.log('Usuário autenticado na página inicial, redirecionando para /game...');
        setTimeout(() => {
            window.location.href = '/game';
        }, 1000);
    } else if (!authStatus.authenticated && window.location.pathname === '/game') {
        console.log('Usuário não autenticado na página do jogo, redirecionando para /...');
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
    }
    
    // Esconder loading
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    
    // Tentar restaurar sessão se houver dados persistentes
    authManager.tryRestoreSession();
});

// Salvar estado antes de sair
window.addEventListener('beforeunload', () => {
    if (authManager.user) {
        console.log('Salvando estado de autenticação antes de sair...');
        localStorage.setItem('firebase_uid', authManager.user.uid);
        localStorage.setItem('last_login', new Date().toISOString());
    }
});