// static/js/auth.js - VERSÃO CORRIGIDA E INTEGRADA
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
        this.setupEventListeners();
        this.checkInitialAuth();
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

    setupEventListeners() {
        // Event listeners para botões existentes
        document.addEventListener('click', (e) => {
            // Login com Google
            if (e.target.id === 'loginButton' || e.target.closest('#loginButton')) {
                this.loginWithGoogle();
            }
            // Logout
            if (e.target.id === 'logoutButton' || e.target.closest('#logoutButton')) {
                this.logout();
            }
        });

        // Enter key nos formulários (se existirem)
        const loginPassword = document.getElementById('login-password');
        if (loginPassword) {
            loginPassword.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.loginWithEmail();
                }
            });
        }

        const registerPassword = document.getElementById('register-password');
        if (registerPassword) {
            registerPassword.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.registerWithEmail();
                }
            });
        }
    }

    async checkInitialAuth() {
        try {
            console.log("🔍 Verificando autenticação inicial...");
            
            // Verificar se já existe um usuário autenticado no Firebase
            const user = firebase.auth().currentUser;
            
            if (user) {
                console.log("👤 Usuário já autenticado no Firebase:", user.email);
                await this.handleUserLogin(user);
            } else {
                console.log("🔐 Nenhum usuário autenticado no Firebase");
                // Verificar se existe sessão no servidor
                await this.checkServerAuth();
            }
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
                    // Usuário tem sessão no servidor, mas não no Firebase
                    console.log("🔄 Sessão servidor encontrada, sincronizando...");
                    this.user = data.user;
                    this.isAuthenticated = true;
                    this.updateUI(this.user);
                    
                    // Redirecionar se estiver na página inicial
                    if (window.location.pathname === '/') {
                        this.redirectToGame();
                    }
                    return;
                }
            }
            
            // Nenhuma sessão ativa
            this.handleUserLogout();
            
        } catch (error) {
            console.error('❌ Erro ao verificar sessão:', error);
            this.handleUserLogout();
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
            
            return result.user;
            
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

    async loginWithEmail() {
        if (this.loginInProgress) return;
        
        const email = document.getElementById('login-email')?.value;
        const password = document.getElementById('login-password')?.value;
        
        if (!email || !password) {
            this.showMessage('Por favor, preencha email e senha', 'error');
            return;
        }

        if (!this.isValidEmail(email)) {
            this.showMessage('Por favor, insira um email válido', 'error');
            return;
        }

        try {
            this.showLoading('Fazendo login...');
            this.loginInProgress = true;
            
            console.log('🔐 Iniciando login com email...');
            const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
            const user = userCredential.user;
            
            console.log('✅ Login com email bem-sucedido!', user.email);
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM EMAIL:', error);
            this.hideLoading();
            this.loginInProgress = false;
            this.showMessage(this.getErrorMessage(error), 'error');
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
        
        if (!this.isValidEmail(email)) {
            this.showMessage('Por favor, insira um email válido', 'error');
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
            
            // Atualizar perfil com nome
            await user.updateProfile({ displayName: name });
            await user.reload(); // Recarregar para pegar o nome atualizado
            
            console.log('✅ Registro bem-sucedido!', user.email);
            
        } catch (error) {
            console.error('❌ ERRO NO REGISTRO:', error);
            this.hideLoading();
            this.loginInProgress = false;
            this.showMessage(this.getErrorMessage(error), 'error');
        }
    }

    async resetPassword() {
        const email = document.getElementById('login-email')?.value || 
                     document.getElementById('register-email')?.value ||
                     prompt('Digite seu e-mail para redefinir a senha:');
        
        if (!email) {
            this.showMessage('Por favor, insira um email.', 'error');
            return;
        }

        if (!this.isValidEmail(email)) {
            this.showMessage('Por favor, insira um email válido', 'error');
            return;
        }

        try {
            this.showLoading('Enviando email de redefinição...');
            await firebase.auth().sendPasswordResetEmail(email);
            this.hideLoading();
            this.showMessage('Email de redefinição enviado! Verifique sua caixa de entrada.', 'success');
        } catch (error) {
            console.error('❌ ERRO AO REDEFINIR SENHA:', error);
            this.hideLoading();
            this.showMessage(this.getErrorMessage(error), 'error');
        }
    }

    async handleUserLogin(user) {
        console.log('👤 Processando login do usuário:', user.email);
        this.user = user;
        
        try {
            // Obter token atualizado
            const token = await user.getIdToken(true);
            console.log('✅ Token obtido, sincronizando com servidor...');
            
            // Sincronizar com servidor backend
            const syncResult = await this.syncWithServer(token);
            
            if (syncResult.success) {
                this.isAuthenticated = true;
                this.updateUI(user);
                
                // Salvar dados localmente
                localStorage.setItem('popcoin_user', JSON.stringify(syncResult.user));
                localStorage.setItem('popcoin_last_login', new Date().toISOString());
                
                console.log('✅ Login sincronizado com servidor');
                
                this.showMessage('Login bem-sucedido!', 'success');
                
                // Redirecionar se estiver na página inicial
                if (window.location.pathname === '/') {
                    this.redirectToGame();
                }
                
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
            this.hideLoading();
            this.loginInProgress = false;
        }
    }

    async syncWithServer(token) {
        try {
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
            console.log('📨 Resposta do servidor:', result);
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
        }
    }

    handleUserLogout() {
        console.log('👋 Processando logout');
        this.user = null;
        this.isAuthenticated = false;
        this.updateUI(null);
        
        // Limpar dados locais
        localStorage.removeItem('popcoin_user');
        localStorage.removeItem('popcoin_last_login');
        
        // Notificar servidor do logout
        this.notifyServerLogout();
        
        // Redirecionar se estiver na página do jogo
        if (window.location.pathname === '/game') {
            this.redirectToHome();
        }
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

    redirectToGame() {
        if (this.redirecting) return;
        
        console.log('➡️ Redirecionando para jogo...');
        this.redirecting = true;
        setTimeout(() => {
            window.location.href = '/game';
        }, 1000);
    }

    redirectToHome() {
        if (this.redirecting) return;
        
        console.log('⬅️ Redirecionando para página inicial...');
        this.redirecting = true;
        setTimeout(() => {
            window.location.href = '/';
        }, 1000);
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para usuário:', user ? user.email : 'null');
        
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
        
        if (this.isAuthenticated) {
            if (gameSection) gameSection.classList.remove('hidden');
            if (welcomeSection) welcomeSection.classList.add('hidden');
        } else {
            if (gameSection) gameSection.classList.add('hidden');
            if (welcomeSection) welcomeSection.classList.remove('hidden');
        }
    }

    hideAuthLoading() {
        const loadingElement = document.getElementById('auth-loading');
        if (loadingElement) {
            loadingElement.classList.add('hidden');
        }
    }

    showLoading(message = 'Processando...') {
        // Sistema de loading consistente com game.js
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
        
        // Sistema de mensagens consistente com game.js
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
            
            // Adicionar estilos CSS
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .auth-message {
                    animation: slideInRight 0.3s ease-out;
                    margin-bottom: 10px;
                    padding: 12px 16px;
                    border-radius: 8px;
                    color: white;
                    font-weight: bold;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }
                .message-success { background: #28a745; }
                .message-error { background: #dc3545; }
                .message-warning { background: #ffc107; color: #000; }
                .message-info { background: #17a2b8; }
            `;
            document.head.appendChild(style);
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `auth-message message-${type}`;
        messageDiv.textContent = message;
        messageContainer.appendChild(messageDiv);
        
        // Auto-remover após 5 segundos
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

    // Métodos públicos para outras partes do sistema
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

// Inicialização global - Padrão consistente com game.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando AuthManager...');
    
    // Configurar estado inicial da UI
    const loginSection = document.getElementById('login-section');
    const authLoading = document.getElementById('auth-loading');
    
    if (loginSection) loginSection.classList.add('hidden');
    if (authLoading) authLoading.classList.remove('hidden');
    
    // Inicializar AuthManager com delay para garantir que Firebase esteja pronto
    setTimeout(() => {
        try {
            console.log('🎯 Criando AuthManager...');
            window.authManager = new AuthManager();
            console.log('✅ Sistema de autenticação inicializado!');
        } catch (error) {
            console.error('❌ Falha crítica na inicialização do AuthManager:', error);
            // Fallback: mostrar interface de login
            const authLoading = document.getElementById('auth-loading');
            const loginSection = document.getElementById('login-section');
            if (authLoading) authLoading.classList.add('hidden');
            if (loginSection) loginSection.classList.remove('hidden');
            window.showMessage('Erro ao carregar sistema de autenticação', 'error');
        }
    }, 100);
});

// Funções globais para compatibilidade com HTML existente
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
    if (window.authManager) {
        if (confirm('Tem certeza que deseja sair?')) {
            window.authManager.logout();
        }
    } else {
        alert('Sistema de autenticação não carregado.');
    }
};

// Export para módulos (se necessário)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}