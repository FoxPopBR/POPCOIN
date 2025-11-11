// static/js/auth.js - VERSÃO SIMPLIFICADA E FUNCIONAL

class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.loginInProgress = false;
        
        console.log('🔄 AuthManager inicializando...');
        this.init();
    }

    init() {
        this.setupAuthListeners();
        this.checkAuthStatus();
        console.log('✅ AuthManager inicializado');
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? `Logado: ${user.email}` : 'Deslogado');
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
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
            
            return result.user;
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM GOOGLE:', error);
            this.hideLoading();
            this.loginInProgress = false;
            
            if (error.code !== 'auth/popup-closed-by-user' && error.code !== 'auth/cancelled-popup-request') {
                this.showMessage('Erro no login com Google: ' + error.message, 'error');
            }
            throw error;
        }
    }

    async loginWithEmail() {
        if (this.loginInProgress) return;
        
        const email = document.getElementById('login-email')?.value;
        const password = document.getElementById('login-password')?.value;
        
        if (!email || !password) {
            this.showMessage('Por favor, preencha email e senha', 'error');
            return;
        }

        try {
            this.showLoading('Fazendo login...');
            this.loginInProgress = true;
            
            console.log('🔐 Iniciando login com email...');
            const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
            const user = userCredential.user;
            
            console.log('✅ Login com email bem-sucedido!', user.email);
            await this.handleUserLogin(user);
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM EMAIL:', error);
            this.hideLoading();
            this.loginInProgress = false;
            
            let errorMessage = 'Erro no login: ';
            switch (error.code) {
                case 'auth/user-not-found':
                    errorMessage += 'Usuário não encontrado.';
                    break;
                case 'auth/wrong-password':
                    errorMessage += 'Senha incorreta.';
                    break;
                case 'auth/invalid-email':
                    errorMessage += 'Email inválido.';
                    break;
                default:
                    errorMessage += error.message;
            }
            
            this.showMessage(errorMessage, 'error');
        }
    }

    async registerWithEmail() {
        if (this.loginInProgress) return;
        
        const name = document.getElementById('register-name')?.value;
        const email = document.getElementById('register-email')?.value;
        const password = document.getElementById('register-password')?.value;
        const confirm = document.getElementById('register-confirm')?.value;
        
        if (!name || !email || !password || !confirm) {
            this.showMessage('Por favor, preencha todos os campos', 'error');
            return;
        }
        
        if (password !== confirm) {
            this.showMessage('As senhas não coincidem', 'error');
            return;
        }
        
        if (password.length < 6) {
            this.showMessage('A senha deve ter pelo menos 6 caracteres', 'error');
            return;
        }

        try {
            this.showLoading('Criando conta...');
            this.loginInProgress = true;
            
            console.log('📝 Iniciando registro com email...');
            const userCredential = await firebase.auth().createUserWithEmailAndPassword(email, password);
            const user = userCredential.user;
            
            await user.updateProfile({ displayName: name });
            console.log('✅ Registro bem-sucedido!', user.email);
            await this.handleUserLogin(user);
            
        } catch (error) {
            console.error('❌ ERRO NO REGISTRO:', error);
            this.hideLoading();
            this.loginInProgress = false;
            
            let errorMessage = 'Erro no registro: ';
            switch (error.code) {
                case 'auth/email-already-in-use':
                    errorMessage += 'Este email já está em uso.';
                    break;
                case 'auth/invalid-email':
                    errorMessage += 'Email inválido.';
                    break;
                case 'auth/weak-password':
                    errorMessage += 'Senha muito fraca.';
                    break;
                default:
                    errorMessage += error.message;
            }
            
            this.showMessage(errorMessage, 'error');
        }
    }

    async resetPassword() {
        const email = prompt('Digite seu e-mail para redefinir a senha:');
        if (!email) {
            this.showMessage('Por favor, insira um email.', 'error');
            return;
        }

        try {
            await firebase.auth().sendPasswordResetEmail(email);
            this.showMessage('Email de redefinição enviado! Verifique sua caixa de entrada.', 'success');
        } catch (error) {
            console.error('❌ ERRO AO REDEFINIR SENHA:', error);
            this.showMessage('Erro ao enviar email de redefinição: ' + error.message, 'error');
        }
    }

    async handleUserLogin(user) {
        console.log('👤 Processando login do usuário:', user.email);
        this.user = user;
        
        try {
            const token = await user.getIdToken();
            console.log('✅ Token obtido, enviando para servidor...');
            
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });

            const result = await response.json();
            console.log('📨 Resposta do servidor:', result);
            
            if (result.success) {
                this.isAuthenticated = true;
                this.updateUI(user);
                
                localStorage.setItem('popcoin_user', JSON.stringify(result.user));
                localStorage.setItem('popcoin_last_login', new Date().toISOString());
                
                console.log('✅ Login sincronizado com servidor');
                
                this.showMessage('Login bem-sucedido! Redirecionando...', 'success');
                setTimeout(() => {
                    window.location.href = '/game';
                }, 1500);
                
            } else {
                throw new Error(result.error || 'Erro no servidor');
            }
        } catch (error) {
            console.error('❌ Erro ao comunicar com servidor:', error);
            this.showMessage('Erro de conexão com o servidor', 'error');
            await this.logout();
        } finally {
            this.hideLoading();
            this.loginInProgress = false;
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout');
        this.user = null;
        this.isAuthenticated = false;
        this.updateUI(null);
        
        localStorage.removeItem('popcoin_user');
        localStorage.removeItem('popcoin_last_login');
        
        if (window.location.pathname === '/game') {
            console.log('⬅️ Redirecionando para /...');
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        }
    }

    async logout() {
        try {
            console.log('🚪 Iniciando logout...');
            await firebase.auth().signOut();
            await fetch('/api/auth/logout', { method: 'POST' });
            this.handleUserLogout();
            console.log('✅ Logout completo realizado');
        } catch (error) {
            console.error('❌ Erro no logout:', error);
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
                
                if (window.location.pathname === '/' && !this.redirecting) {
                    console.log("➡️ Redirecionando para jogo...");
                    this.redirecting = true;
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1000);
                }
            } else {
                this.isAuthenticated = false;
                if (window.location.pathname === '/game' && !this.redirecting) {
                    console.log("⬅️ Redirecionando para início...");
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

            if (!this.isAuthenticated) {
                this.showLoginUI();
            }
        }
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para usuário:', user ? user.email : 'null');
        
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');

        if (user) {
            if (user.photoURL && userPic) {
                userPic.src = user.photoURL;
                userPic.style.display = 'inline';
            }
            if (userName) {
                userName.textContent = user.displayName || user.email || 'Usuário';
            }
            if (userInfo) userInfo.classList.remove('hidden');
            if (loginSection) loginSection.classList.add('hidden');
        } else {
            if (userInfo) userInfo.classList.add('hidden');
            if (loginSection) loginSection.classList.remove('hidden');
        }
    }

    hideAuthLoading() {
        const loadingElement = document.getElementById('auth-loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    }

    showLoginUI() {
        const loadingElement = document.getElementById('auth-loading');
        const loginSection = document.getElementById('login-section');
        if (loadingElement) loadingElement.style.display = 'none';
        if (loginSection) loginSection.classList.remove('hidden');
    }

    showLoading(message = 'Processando...') {
        if (window.showGlobalLoading) {
            window.showGlobalLoading(message);
        }
    }

    hideLoading() {
        if (window.hideGlobalLoading) {
            window.hideGlobalLoading();
        }
    }

    showMessage(message, type = 'info') {
        console.log(`💬 ${type}: ${message}`);
        
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#ff4444' : type === 'success' ? '#44ff44' : '#4488ff'};
            color: white;
            border-radius: 5px;
            z-index: 10000;
            font-weight: bold;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            max-width: 400px;
            word-wrap: break-word;
        `;
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);
        
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.style.opacity = '0';
                messageDiv.style.transition = 'opacity 0.5s ease';
                setTimeout(() => {
                    if (messageDiv.parentNode) {
                        document.body.removeChild(messageDiv);
                    }
                }, 500);
            }
        }, 5000);
    }
}

// Inicialização global
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando AuthManager...');
    
    // Esconder seção de login inicialmente
    const loginSection = document.getElementById('login-section');
    if (loginSection) {
        loginSection.classList.add('hidden');
    }
    
    // Mostrar loading inicial
    const loadingElement = document.getElementById('auth-loading');
    if (loadingElement) {
        loadingElement.style.display = 'flex';
    }
    
    // Inicializar AuthManager
    setTimeout(() => {
        console.log('🎯 Criando AuthManager...');
        window.authManager = new AuthManager();
        console.log('✅ Sistema de autenticação inicializado!');
    }, 500);
});

// Funções globais
window.loginWithGoogle = function() {
    if (window.authManager) {
        window.authManager.loginWithGoogle();
    } else {
        alert('Sistema de autenticação não carregado. Recarregue a página.');
    }
};

window.loginWithEmail = function() {
    if (window.authManager) {
        window.authManager.loginWithEmail();
    } else {
        alert('Sistema de autenticação não carregado. Recarregue a página.');
    }
};

window.registerWithEmail = function() {
    if (window.authManager) {
        window.authManager.registerWithEmail();
    } else {
        alert('Sistema de autenticação não carregado. Recarregue a página.');
    }
};

window.resetPassword = function() {
    if (window.authManager) {
        window.authManager.resetPassword();
    } else {
        alert('Sistema de autenticação não carregado. Recarregue a página.');
    }
};

window.logout = function() {
    if (window.authManager && confirm('Tem certeza que deseja sair?')) {
        window.authManager.logout();
    }
};