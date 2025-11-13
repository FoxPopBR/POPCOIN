// static/js/auth.js - VERSÃO SIMPLIFICADA COM SESSIONSTORAGE
class AuthManager {
    constructor() {
        this.user = null;
        this.isAuthenticated = false;
        this.initialized = false;
        this.currentToken = null;
        
        console.log('🔄 AuthManager inicializando...');
    }

    async init() {
        if (this.initialized) return;

        try {
            console.log('🔥 Configurando AuthManager...');
            this.setupAuthListeners();
            this.setupEventListeners();
            
            // Verificar se já tem token salvo (APENAS sessionStorage)
            await this.checkStoredToken();
            
            this.initialized = true;
            console.log('✅ AuthManager inicializado com sucesso');
        } catch (error) {
            console.error('❌ Falha na inicialização:', error);
        }
    }

    setupAuthListeners() {
        console.log('🔥 Configurando observador do Firebase Auth...');
        
        firebase.auth().onAuthStateChanged(async (user) => {
            console.log('🔄 Firebase auth state changed:', user ? user.email : 'Deslogado');
            
            if (user) {
                await this.handleUserLogin(user);
            } else {
                this.handleUserLogout();
            }
        });
    }

    setupEventListeners() {
        // Logout button
        document.addEventListener('click', (e) => {
            if (e.target.id === 'logoutButton' || e.target.closest('#logoutButton')) {
                e.preventDefault();
                this.logout();
            }
        });
    }

    async checkStoredToken() {
        try {
            // ✅ APENAS sessionStorage - some quando fecha janela
            const storedToken = sessionStorage.getItem('firebase_token');
            
            if (storedToken) {
                console.log("🔍 Token encontrado no sessionStorage, verificando validade...");
                
                // Verificar se o token ainda é válido
                const response = await fetch('/api/auth/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: storedToken })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.user) {
                        console.log("✅ Token válido, restaurando sessão:", data.user.email);
                        this.currentToken = storedToken;
                        this.user = data.user;
                        this.isAuthenticated = true;
                        this.updateUI(this.user);
                        return true;
                    }
                }
                
                // Token inválido, remover
                console.log("⚠️ Token inválido, removendo...");
                sessionStorage.removeItem('firebase_token');
            }
            
            console.log("🔍 Nenhum token válido encontrado - login necessário");
            return false;
            
        } catch (error) {
            console.error('❌ Erro ao verificar token armazenado:', error);
            sessionStorage.removeItem('firebase_token');
            return false;
        }
    }

    async loginWithGoogle() {
        try {
            console.log('🔑 Iniciando login com Google...');
            
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
            // 🔥 OBTER TOKEN DO FIREBASE
            const token = await user.getIdToken();
            console.log('✅ Token obtido do Firebase');
            
            // 🔥 SALVAR TOKEN NO SESSIONSTORAGE (some quando fecha janela)
            this.currentToken = token;
            sessionStorage.setItem('firebase_token', token);
            
            // Extrair informações básicas do usuário
            this.user = {
                uid: user.uid,
                email: user.email,
                name: user.displayName || user.email.split('@')[0],
                picture: user.photoURL || '/static/images/default-avatar.png',
                email_verified: user.emailVerified
            };
            
            this.isAuthenticated = true;
            
            // 🔥 VERIFICAR SE PRECISA CRIAR USUÁRIO NO BANCO
            try {
                const response = await this.authFetch('/api/user/profile', {
                    method: 'GET'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.profile) {
                        // Mesclar dados do banco
                        this.user = { ...this.user, ...data.profile };
                        console.log('✅ Dados do usuário carregados do banco');
                    }
                }
            } catch (error) {
                console.warn('⚠️ Não foi possível carregar dados do banco:', error);
            }
            
            this.updateUI(this.user);
            
            console.log('✅ Login completo');
            
            // Redirecionamento inteligente
            this.handlePostLoginRedirect();
            
        } catch (error) {
            console.error('❌ Erro ao processar login:', error);
            await firebase.auth().signOut();
            sessionStorage.removeItem('firebase_token');
            alert('Erro ao conectar. Tente novamente.');
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
        this.currentToken = null;
        sessionStorage.removeItem('firebase_token');
        this.updateUI(null);
    }

    async logout() {
        try {
            console.log('🚪 Iniciando logout completo...');
            
            // 1. Fazer logout no Firebase
            await firebase.auth().signOut();
            
            // 2. Limpar estado local
            this.handleUserLogout();
            
            console.log('✅ Logout completo realizado');
            
            // 3. Redirecionar para home
            window.location.href = '/';
            
        } catch (error) {
            console.error('❌ Erro no logout:', error);
            this.handleUserLogout();
            window.location.href = '/';
        }
    }

    // 🔥 FUNÇÃO PRINCIPAL - authFetch
    async authFetch(url, options = {}) {
        try {
            // Pegar token atual (apenas sessionStorage)
            let token = this.currentToken || sessionStorage.getItem('firebase_token');
            
            // Se não tem token, verificar se usuário está logado no Firebase
            if (!token) {
                const user = firebase.auth().currentUser;
                if (user) {
                    token = await user.getIdToken();
                    this.currentToken = token;
                    sessionStorage.setItem('firebase_token', token);
                } else {
                    // Sem usuário, redirecionar para login
                    console.log('❌ Usuário não autenticado');
                    window.location.href = '/';
                    throw new Error('Usuário não autenticado');
                }
            }
            
            // Adicionar token ao header
            if (token) {
                options.headers = {
                    ...options.headers,
                    'Authorization': `Bearer ${token}`
                };
            }
            
            // Fazer requisição
            let response = await fetch(url, options);
            
            // 🔥 SE TOKEN EXPIRADO, RENOVAR E TENTAR NOVAMENTE
            if (response.status === 401) {
                console.log('🔄 Token expirado, renovando...');
                
                const user = firebase.auth().currentUser;
                if (user) {
                    // Forçar renovação do token
                    const newToken = await user.getIdToken(true);
                    this.currentToken = newToken;
                    sessionStorage.setItem('firebase_token', newToken);
                    
                    // Atualizar header e tentar novamente
                    options.headers['Authorization'] = `Bearer ${newToken}`;
                    response = await fetch(url, options);
                    
                    console.log('✅ Token renovado e requisição refeita');
                } else {
                    // Sem usuário, redirecionar para login
                    console.log('❌ Usuário não autenticado');
                    window.location.href = '/';
                }
            }
            
            return response;
            
        } catch (error) {
            console.error('❌ Erro no authFetch:', error);
            throw error;
        }
    }

    updateUI(user) {
        console.log('🎨 Atualizando UI para:', user ? user.email : 'null');
        
        // Evento para atualizar outros componentes
        const event = new CustomEvent('authStateChanged', {
            detail: { 
                isAuthenticated: !!user, 
                user: user 
            }
        });
        window.dispatchEvent(event);
        
        // Atualizar elementos da UI
        const userInfo = document.getElementById('user-info');
        const loginSection = document.getElementById('login-section');
        const userPic = document.getElementById('user-pic');
        const userName = document.getElementById('user-name');
        
        if (user) {
            // Avatar com fallback robusto
            if (userPic) {
                const avatarUrl = user.picture || user.photoURL || '/static/images/default-avatar.png';
                userPic.src = avatarUrl;
                userPic.onerror = function() {
                    console.log('❌ Erro ao carregar avatar, usando fallback');
                    this.src = '/static/images/default-avatar.png';
                    this.onerror = null;
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
        
        // Redirecionar apenas se estiver na home
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

// 🔥 EXPORTAR authFetch GLOBALMENTE
window.authFetch = (url, options) => {
    if (window.authManager) {
        return window.authManager.authFetch(url, options);
    } else {
        console.warn('⚠️ AuthManager não inicializado, usando fetch normal');
        return fetch(url, options);
    }
};