// static/js/auth.js - VERSÃO COMPLETAMENTE CORRIGIDA

class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.loginInProgress = false; // NOVO: prevenir múltiplos logins
        this.setupAuthListeners();
        this.checkAuthStatus();
        this.setupButtonListeners(); // NOVO: configuração específica de botões
    }

    // NOVO: Sistema dedicado de configuração de botões
    setupButtonListeners() {
        console.log('🔘 Configurando listeners específicos...');
        
        // Botões Google - apenas os que devem fazer login Google
        const googleButtons = document.querySelectorAll('.btn-google, [onclick*="loginWithGoogle"]');
        googleButtons.forEach(button => {
            button.replaceWith(button.cloneNode(true)); // Remove listeners antigos
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🎯 Botão Google clicado!');
                this.loginWithGoogle();
            });
        });

        // Botão de login com email específico
        const emailLoginBtn = document.querySelector('[onclick*="loginWithEmail"]');
        if (emailLoginBtn) {
            emailLoginBtn.replaceWith(emailLoginBtn.cloneNode(true));
            emailLoginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🎯 Botão Email Login clicado!');
                this.loginWithEmail();
            });
        }

        // Botão de registro com email específico
        const emailRegisterBtn = document.querySelector('[onclick*="registerWithEmail"]');
        if (emailRegisterBtn) {
            emailRegisterBtn.replaceWith(emailRegisterBtn.cloneNode(true));
            emailRegisterBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🎯 Botão Email Register clicado!');
                this.registerWithEmail();
            });
        }
    }

    // NOVO: Sistema de loading durante login
    showLoginLoading() {
        this.loginInProgress = true;
        const loadingOverlay = document.getElementById('loading-overlay-index') || this.createLoadingOverlay();
        loadingOverlay.style.display = 'flex';
        console.log('⏳ Mostrando loading de login...');
    }

    hideLoginLoading() {
        this.loginInProgress = false;
        const loadingOverlay = document.getElementById('loading-overlay-index');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'none';
        }
        console.log('✅ Escondendo loading de login...');
    }

    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay-index';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            flex-direction: column;
            color: white;
            font-family: Arial, sans-serif;
        `;
        
        overlay.innerHTML = `
            <div class="loading-spinner" style="
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            "></div>
            <h3>Processando login...</h3>
            <p>Aguarde enquanto autenticamos sua conta</p>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
        
        document.body.appendChild(overlay);
        return overlay;
    }

    async loginWithGoogle() {
        if (this.loginInProgress) {
            console.log('⏳ Login já em andamento...');
            return;
        }

        try {
            this.showLoginLoading();
            console.log('🔐 INICIANDO LOGIN COM GOOGLE...');
            
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            provider.setCustomParameters({
                prompt: 'select_account'
            });
            
            console.log('🪟 Abrindo popup do Google...');
            const result = await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google bem-sucedido!', result.user.email);
            return result.user;
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM GOOGLE:', error);
            this.hideLoginLoading();
            
            let errorMessage = 'Erro no login: ';
            let showAlert = true;
            
            switch (error.code) {
                case 'auth/popup-blocked':
                    errorMessage += 'Popup bloqueado. Permita popups para este site.';
                    break;
                case 'auth/popup-closed-by-user':
                    errorMessage += 'Popup fechado. Tente novamente.';
                    showAlert = false;
                    break;
                case 'auth/cancelled-popup-request':
                    errorMessage += 'Popup cancelado. Tente novamente.';
                    showAlert = false;
                    break;
                case 'auth/network-request-failed':
                    errorMessage += 'Erro de rede. Verifique sua conexão.';
                    break;
                default:
                    errorMessage += error.message;
            }
            
            if (showAlert) {
                this.showMessage(errorMessage, 'error');
            }
            throw error;
        }
    }

    // NOVO: Funções de email COMPLETAS e CORRETAS
    async loginWithEmail() {
        if (this.loginInProgress) return;
        
        const email = document.getElementById('login-email')?.value;
        const password = document.getElementById('login-password')?.value;
        
        if (!email || !password) {
            this.showMessage('Por favor, preencha email e senha', 'error');
            return;
        }

        try {
            this.showLoginLoading();
            console.log('🔐 Iniciando login com email...');
            
            const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
            const user = userCredential.user;
            
            console.log('✅ Login com email bem-sucedido!', user.email);
            await this.handleUserLogin(user);
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM EMAIL:', error);
            this.hideLoginLoading();
            
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
                case 'auth/user-disabled':
                    errorMessage += 'Esta conta foi desativada.';
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
            this.showLoginLoading();
            console.log('📝 Iniciando registro com email...');
            
            const userCredential = await firebase.auth().createUserWithEmailAndPassword(email, password);
            const user = userCredential.user;
            
            // Atualizar perfil com nome
            await user.updateProfile({
                displayName: name
            });
            
            console.log('✅ Registro bem-sucedido!', user.email);
            await this.handleUserLogin(user);
            
        } catch (error) {
            console.error('❌ ERRO NO REGISTRO:', error);
            this.hideLoginLoading();
            
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
                case 'auth/operation-not-allowed':
                    errorMessage += 'Operação não permitida.';
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
                
                // Redirecionar com loading
                this.showMessage('Login bem-sucedido! Redirecionando...', 'success');
                setTimeout(() => {
                    window.location.href = '/game';
                }, 2000);
                
            } else {
                throw new Error(result.error || 'Erro no servidor');
            }
        } catch (error) {
            console.error('❌ Erro ao comunicar com servidor:', error);
            this.showMessage('Erro de conexão com o servidor', 'error');
            await this.logout();
        } finally {
            this.hideLoginLoading();
        }
    }

    // ... (resto das funções permanecem iguais - handleUserLogout, logout, checkAuthStatus, etc.)

    updateUI(user) {
        console.log('🎨 Atualizando UI para usuário:', user ? user.email : 'null');
        
        // CORREÇÃO: Atualizar apenas UM avatar - remover o duplicado
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');

        if (user) {
            // Usuário logado - mostrar apenas UM avatar
            if (userPic) {
                userPic.src = user.photoURL || '/static/images/default-avatar.png';
                userPic.style.display = 'inline';
                userPic.alt = `Foto de ${user.displayName || user.email}`;
            }
            if (userName) {
                userName.textContent = user.displayName || user.email || 'Usuário';
            }
            if (userInfo) userInfo.style.display = 'flex';
            if (loginSection) loginSection.style.display = 'none';
        } else {
            // Usuário não logado
            if (userInfo) userInfo.style.display = 'none';
            if (loginSection) loginSection.style.display = 'block';
        }
    }

    // ... (resto do código permanece igual)
}

// Inicialização CORRIGIDA
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando AuthManager...');
    
    // Esconder seção de login inicialmente
    const loginSection = document.getElementById('login-section');
    if (loginSection) loginSection.style.display = 'none';
    
    // Mostrar loading inicial
    const loadingElement = document.getElementById('auth-loading');
    if (loadingElement) loadingElement.style.display = 'flex';
    
    // Inicializar AuthManager
    setTimeout(() => {
        console.log('🎯 Criando AuthManager...');
        window.authManager = new AuthManager();
        console.log('✅ Sistema de autenticação inicializado!');
    }, 1000);
});

// REMOVER funções globais conflitantes - usar apenas os métodos da classe
// Manter apenas logout global se necessário
window.logout = function() {
    if (window.authManager) {
        window.authManager.logout();
    }
};