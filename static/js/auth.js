// Gerenciamento de autenticação

class AuthManager {
    constructor() {
        this.user = null;
        this.initFirebase();
        this.setupAuthListeners();
    }

    initFirebase() {
        // Firebase já inicializado no base.html
        console.log('Firebase inicializado');
    }

    setupAuthListeners() {
        // Observar mudanças no estado de autenticação
        firebase.auth().onAuthStateChanged((user) => {
            if (user) {
                this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
    }

    async handleUserLogin(user) {
        this.user = user;
        
        // Obter token do Firebase
        const token = await user.getIdToken();
        
        try {
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
                console.log('Login bem-sucedido:', user.displayName);
                
                // Redirecionar para o jogo se estiver na página inicial
                if (window.location.pathname === '/') {
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                console.error('Erro no login:', result.error);
                this.handleUserLogout();
            }
        } catch (error) {
            console.error('Erro ao comunicar com servidor:', error);
        }
    }

    handleUserLogout() {
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
            userPic.src = user.photoURL || '/static/images/default-avatar.png';
            userName.textContent = user.displayName || 'Usuário';
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
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            const result = await firebase.auth().signInWithPopup(provider);
            return result.user;
        } catch (error) {
            console.error('Erro no login com Google:', error);
            alert('Erro no login: ' + error.message);
            throw error;
        }
    }

    // Logout
    async logout() {
        try {
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
window.loginWithGoogle = () => authManager.loginWithGoogle();
window.logout = () => authManager.logout();

// Verificar status ao carregar a página
document.addEventListener('DOMContentLoaded', async () => {
    const authStatus = await authManager.checkAuthStatus();
    
    if (authStatus.authenticated && window.location.pathname === '/') {
        // Se já estiver autenticado e na página inicial, redirecionar para o jogo
        window.location.href = '/game';
    }
});