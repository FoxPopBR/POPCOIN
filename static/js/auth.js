// static/js/auth.js - VERSÃO CORRIGIDA
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.authChecked = false;
        this.redirecting = false;
        this.setupAuthListeners();
        this.checkAuthStatus();
        // CORREÇÃO: Remover setupButtonListeners duplicado
    }

    // CORREÇÃO: Remover setupButtonListeners duplicado - já está no DOMContentLoaded global

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
        try {
            console.log('🔐 INICIANDO LOGIN COM GOOGLE...');
            
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            // Forçar seleção de conta
            provider.setCustomParameters({
                prompt: 'select_account'
            });
            
            console.log('🪟 Abrindo popup do Google...');
            const result = await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google bem-sucedido!', result.user.email);
            return result.user;
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM GOOGLE:', error);
            
            let errorMessage = 'Erro no login: ';
            let showAlert = true;
            
            switch (error.code) {
                case 'auth/popup-blocked':
                    errorMessage += 'Popup bloqueado. Permita popups para este site.';
                    break;
                case 'auth/popup-closed-by-user':
                    errorMessage += 'Popup fechado pelo usuário.';
                    showAlert = false;
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
            
            console.error('❌ Detalhes do erro:', error);
            
            if (showAlert) {
                this.showMessage(errorMessage, 'error');
            }
            throw error;
        }
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
        try {
            console.log('🔐 INICIANDO LOGIN COM GOOGLE...');
            
            const provider = new firebase.auth.GoogleAuthProvider();
            provider.addScope('profile');
            provider.addScope('email');
            
            // Forçar seleção de conta
            provider.setCustomParameters({
                prompt: 'select_account'
            });
            
            console.log('🪟 Abrindo popup do Google...');
            const result = await firebase.auth().signInWithPopup(provider);
            console.log('✅ Login com Google bem-sucedido!', result.user.email);
            return result.user;
            
        } catch (error) {
            console.error('❌ ERRO NO LOGIN COM GOOGLE:', error);
            
            let errorMessage = 'Erro no login: ';
            let showAlert = true;
            
            switch (error.code) {
                case 'auth/popup-blocked':
                    errorMessage += 'Popup bloqueado. Permita popups para este site.';
                    break;
                case 'auth/popup-closed-by-user':
                    errorMessage += 'Popup fechado pelo usuário.';
                    showAlert = false; // Não mostrar alerta para fechamento normal
                    break;
                case 'auth/unauthorized-domain':
                    errorMessage += 'Domínio não autorizado. Verifique as configurações do Firebase.';
                    break;
                case 'auth/network-request-failed':
                    errorMessage += 'Erro de rede. Verifique sua conexão.';
                    break;
                case 'auth/cancelled-popup-request':
                    errorMessage += 'Popup cancelado.';
                    showAlert = false;
                    break;
                default:
                    errorMessage += error.message;
            }
            
            console.error('❌ Detalhes do erro:', error);
            
            if (showAlert) {
                this.showMessage(errorMessage, 'error');
            }
            throw error;
        }
    }

    async handleUserLogin(user) {
        console.log('👤 Processando login do usuário:', user.email);
        this.user = user;
        
        try {
            // Obter token do Firebase
            console.log('🔐 Obtendo token Firebase...');
            const token = await user.getIdToken();
            console.log('✅ Token obtido, enviando para servidor...');
            
            // Enviar token para o servidor
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token })
            });

            console.log('📡 Aguardando resposta do servidor...');
            const result = await response.json();
            console.log('📨 Resposta do servidor:', result);
            
            if (result.success) {
                this.isAuthenticated = true;
                this.updateUI(user);
                
                // Salvar no localStorage para persistência
                localStorage.setItem('popcoin_user', JSON.stringify(result.user));
                localStorage.setItem('popcoin_last_login', new Date().toISOString());
                
                console.log('✅ Login sincronizado com servidor');
                
                // Redirecionar para o jogo após login bem-sucedido
                if (window.location.pathname === '/') {
                    console.log('➡️ Redirecionando para /game...');
                    setTimeout(() => {
                        window.location.href = '/game';
                    }, 1500);
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
            console.log('⬅️ Redirecionando para /...');
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
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
            console.log("🔍 Verificando status de autenticação no servidor...");
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

            // CORREÇÃO ADICIONADA: Se não autenticado, garantir exibição do botão de login
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
            console.log('👋 Escondendo loading...');
            loadingElement.style.display = 'none';
        }
    }

    // CORREÇÃO ADICIONADA: Função para mostrar a interface de login
    showLoginUI() {
        const loadingElement = document.getElementById('auth-loading');
        const loginSection = document.getElementById('login-section');
        if (loadingElement) loadingElement.style.display = 'none';
        if (loginSection) loginSection.style.display = 'block';
        console.log('✅ Interface de login exibida.');
    }

    showMessage(message, type = 'info') {
        console.log(`💬 ${type}: ${message}`);
        
        // Sistema de mensagens melhorado
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

// Inicialização global com mais logs
let authManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, configurando botões Google...');
    
    // Configurar todos os botões Google
    function setupGoogleButtons() {
        // Selecionar por ID específico
        const loginButton = document.getElementById('loginButton');
        if (loginButton) {
            console.log('✅ Botão loginButton encontrado');
            loginButton.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('🎯 Botão loginButton clicado!');
                if (window.authManager) {
                    window.authManager.loginWithGoogle();
                } else {
                    console.error('❌ AuthManager não disponível');
                    alert('Sistema de autenticação não carregado. Recarregue a página.');
                }
            });
        }

        // Selecionar por classe
        const googleButtons = document.querySelectorAll('.btn-google');
        googleButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('🎯 Botão Google (classe) clicado!');
                if (window.authManager) {
                    window.authManager.loginWithGoogle();
                }
            });
        });

        // Selecionar por texto
        const allButtons = document.querySelectorAll('button');
        allButtons.forEach(button => {
            if (button.textContent.includes('Google') || button.textContent.includes('Entrar com')) {
                if (!button.hasAttribute('data-google-bound')) {
                    button.setAttribute('data-google-bound', 'true');
                    button.addEventListener('click', function(e) {
                        e.preventDefault();
                        console.log('🎯 Botão Google (texto) clicado!');
                        if (window.authManager) {
                            window.authManager.loginWithGoogle();
                        }
                    });
                }
            }
        });
    }

    // Executar imediatamente e também após 1 segundo (para conteúdo dinâmico)
    setupGoogleButtons();
    setTimeout(setupGoogleButtons, 1000);
    setTimeout(setupGoogleButtons, 3000); // Backup

    // Inicializar AuthManager
    setTimeout(() => {
        console.log('🎯 Criando AuthManager...');
        window.authManager = new AuthManager();
        console.log('✅ Sistema de autenticação inicializado!');
    }, 500);
});

// Função global para compatibilidade
window.loginWithGoogle = function() {
    console.log('🌐 Função global loginWithGoogle chamada');
    if (window.authManager) {
        window.authManager.loginWithGoogle();
    } else {
        console.error('❌ AuthManager não inicializado');
        setTimeout(() => {
            if (window.authManager) {
                window.authManager.loginWithGoogle();
            } else {
                alert('Sistema de autenticação não carregado. Recarregue a página.');
            }
        }, 1000);
    }
};

window.logout = () => {
    console.log('🌐 Função global logout chamada');
    if (window.authManager) {
        if (confirm('Tem certeza que deseja sair?')) {
            window.authManager.logout();
        }
    } else {
        console.error('❌ AuthManager não inicializado');
    }
};