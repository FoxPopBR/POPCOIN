// Gerenciamento de autenticação
class AuthManager {
    constructor() {
        this.user = null;
        this.initFirebase();
        this.setupAuthListeners();
    }

    initFirebase() {
        console.log('Firebase configurado, aguardando inicialização...');
    }

    setupAuthListeners() {
        // Observar mudanças no estado de autenticação
        firebase.auth().onAuthStateChanged((user) => {
            console.log('Estado de autenticação alterado:', user);
            if (user) {
                this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
    }

    async handleUserLogin(user) {
        console.log('Usuário logado no Firebase:', user);
        this.user = user;
        
        try {
            // Obter token do Firebase
            const token = await user.getIdToken();
            console.log('Token obtido, enviando para servidor...');
            
            // Enviar token para o servidor
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token })
            });

            const result = await response.json();
            console.log('Resposta do servidor:', result);
            
            if (result.success) {
                this.updateUI(user);
                console.log('Login bem-sucedido:', user.displayName);
                
                // Redirecionar para o jogo se estiver na página inicial
                if (window.location.pathname === '/') {
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                console.error('Erro no login no servidor:', result.error);
                await this.logout();
            }
        } catch (error) {
            console.error('Erro ao comunicar com servidor:', error);
            alert('Erro de comunicação com o servidor: ' + error.message);
        }
    }

    handleUserLogout() {
        console.log('Usuário deslogado');
        this.user = null;
        this.updateUI(null);
        
        // Se estiver na página do jogo, redirecionar para início
        if (window.location.pathname === '/game') {
            window.location.href = '/';
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
            
            console.log('Abrindo popup de autenticação...');
            const result = await firebase.auth().signInWithPopup(provider);
            console.log('Login com Google bem-sucedido:', result.user);
            return result.user;
        } catch (error) {
            console.error('Erro detalhado no login com Google:', error);
            
            // Tratamento específico de erros
            let errorMessage = 'Erro no login: ';
            
            switch (error.code) {
                case 'auth/popup-blocked':
                    errorMessage += 'Popup bloqueado pelo navegador. Por favor, permita popups para este site.';
                    break;
                case 'auth/popup-closed-by-user':
                    errorMessage += 'Popup fechado pelo usuário.';
                    break;
                case 'auth/unauthorized-domain':
                    errorMessage += 'Domínio não autorizado. Verifique as configurações do Firebase.';
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
            console.log('Fazendo logout...');
            // Fazer logout no Firebase
            await firebase.auth().signOut();
            
            // Fazer logout no servidor
            await fetch('/api/auth/logout');
            
            this.handleUserLogout();
        } catch (error) {
            console.error('Erro no logout:', error);
        }
    }

    // Verificar status de autenticação
    async checkAuthStatus() {
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Erro ao verificar status:', error);
            return { authenticated: false };
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
    authManager.logout();
};

// Verificar status ao carregar a página
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Página carregada, verificando autenticação...');
    const authStatus = await authManager.checkAuthStatus();
    console.log('Status de autenticação:', authStatus);
    
    if (authStatus.authenticated && window.location.pathname === '/') {
        console.log('Usuário já autenticado, redirecionando para /game');
        window.location.href = '/game';
    }
});