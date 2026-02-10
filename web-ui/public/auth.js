/**
 * Xmore — Frontend Authentication Module
 * Handles auth modal, login/signup, session state, and bilingual text.
 */

// ============================================
// STATE
// ============================================
let currentUser = null;
let authMode = 'login'; // 'login' or 'signup'

// ============================================
// BILINGUAL TEXT
// ============================================
const authText = {
    en: {
        auth_welcome: '🔐 Welcome to Xmore',
        auth_login_tab: 'Login',
        auth_signup_tab: 'Sign Up',
        auth_email: 'Email',
        auth_password: 'Password',
        auth_login_btn: 'Login',
        auth_signup_btn: 'Sign Up',
        auth_logout: 'Logout',
        auth_login_prompt: '🔐 Login / Sign Up',
        auth_logged_in_as: 'Logged in as',
        auth_err_invalid: 'Invalid email or password',
        auth_err_exists: 'Signup failed. Please try again.',
        auth_err_short_pw: 'Password must be at least 8 characters',
        auth_err_rate: 'Too many attempts. Try again in a minute.',
        auth_err_generic: 'Something went wrong. Please try again.',
        auth_err_email_invalid: 'Invalid email format',
        auth_err_required: 'Email and password required',
    },
    ar: {
        auth_welcome: '🔐 مرحباً بك في Xmore',
        auth_login_tab: 'تسجيل دخول',
        auth_signup_tab: 'حساب جديد',
        auth_email: 'البريد الإلكتروني',
        auth_password: 'كلمة المرور',
        auth_login_btn: 'تسجيل الدخول',
        auth_signup_btn: 'إنشاء حساب',
        auth_logout: 'تسجيل خروج',
        auth_login_prompt: '🔐 تسجيل دخول / حساب جديد',
        auth_logged_in_as: 'مسجّل الدخول بـ',
        auth_err_invalid: 'البريد أو كلمة المرور غير صحيحة',
        auth_err_exists: 'فشل التسجيل. حاول مرة أخرى.',
        auth_err_short_pw: 'كلمة المرور يجب أن تكون 8 أحرف على الأقل',
        auth_err_rate: 'محاولات كثيرة. حاول بعد دقيقة.',
        auth_err_generic: 'حدث خطأ. حاول مرة أخرى.',
        auth_err_email_invalid: 'صيغة البريد الإلكتروني غير صحيحة',
        auth_err_required: 'البريد الإلكتروني وكلمة المرور مطلوبان',
    }
};

function at(key) {
    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';
    return (authText[lang] && authText[lang][key]) || authText.en[key] || key;
}

// ============================================
// DOM ELEMENTS
// ============================================
function getAuthElements() {
    return {
        modal: document.getElementById('authModal'),
        closeBtn: document.getElementById('authCloseBtn'),
        welcome: document.getElementById('authWelcome'),
        loginTab: document.getElementById('authLoginTab'),
        signupTab: document.getElementById('authSignupTab'),
        form: document.getElementById('authForm'),
        emailInput: document.getElementById('authEmail'),
        passwordInput: document.getElementById('authPassword'),
        emailLabel: document.getElementById('authEmailLabel'),
        passwordLabel: document.getElementById('authPasswordLabel'),
        submitBtn: document.getElementById('authSubmitBtn'),
        error: document.getElementById('authError'),
        userInfoBar: document.getElementById('userInfoBar'),
        userEmail: document.getElementById('userEmail'),
        logoutBtn: document.getElementById('logoutBtn'),
        loginPrompt: document.getElementById('loginPrompt'),
        showAuthBtn: document.getElementById('showAuthBtn'),
        watchlistTab: document.getElementById('tabWatchlist'),
    };
}

// ============================================
// AUTH MODAL
// ============================================
function showAuthModal(mode = 'login') {
    const els = getAuthElements();
    if (!els.modal) return;

    authMode = mode;
    els.modal.style.display = 'flex';
    els.error.style.display = 'none';
    els.emailInput.value = '';
    els.passwordInput.value = '';

    updateAuthModalText();
    els.emailInput.focus();
}

function hideAuthModal() {
    const els = getAuthElements();
    if (els.modal) els.modal.style.display = 'none';
}

function updateAuthModalText() {
    const els = getAuthElements();
    if (!els.modal) return;

    els.welcome.textContent = at('auth_welcome');
    els.loginTab.textContent = at('auth_login_tab');
    els.signupTab.textContent = at('auth_signup_tab');
    els.emailLabel.textContent = at('auth_email');
    els.passwordLabel.textContent = at('auth_password');

    if (authMode === 'login') {
        els.loginTab.classList.add('active');
        els.signupTab.classList.remove('active');
        els.submitBtn.textContent = at('auth_login_btn');
        els.passwordInput.setAttribute('autocomplete', 'current-password');
    } else {
        els.signupTab.classList.add('active');
        els.loginTab.classList.remove('active');
        els.submitBtn.textContent = at('auth_signup_btn');
        els.passwordInput.setAttribute('autocomplete', 'new-password');
    }
}

function showAuthError(message) {
    const els = getAuthElements();
    els.error.textContent = message;
    els.error.style.display = 'block';
}

// ============================================
// AUTH API CALLS
// ============================================
async function handleAuthSubmit(e) {
    e.preventDefault();
    const els = getAuthElements();
    const email = els.emailInput.value.trim();
    const password = els.passwordInput.value;

    // Client-side validation
    if (!email || !password) {
        return showAuthError(at('auth_err_required'));
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        return showAuthError(at('auth_err_email_invalid'));
    }
    if (authMode === 'signup' && password.length < 8) {
        return showAuthError(at('auth_err_short_pw'));
    }

    els.submitBtn.disabled = true;
    els.error.style.display = 'none';

    try {
        const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/signup';
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password }),
        });

        const data = await res.json();

        if (res.ok && data.success) {
            currentUser = data.user;
            hideAuthModal();
            setLoggedInState(data.user);
            // Reload watchlist if on that tab
            if (typeof loadWatchlist === 'function') loadWatchlist();
        } else {
            // Map server errors to localized messages
            const errMsg = data.error || '';
            if (res.status === 429) {
                showAuthError(at('auth_err_rate'));
            } else if (errMsg.includes('at least 8')) {
                showAuthError(at('auth_err_short_pw'));
            } else if (errMsg.includes('Invalid email or password')) {
                showAuthError(at('auth_err_invalid'));
            } else if (errMsg.includes('Signup failed')) {
                showAuthError(at('auth_err_exists'));
            } else {
                showAuthError(errMsg || at('auth_err_generic'));
            }
        }
    } catch (err) {
        console.error('Auth error:', err);
        showAuthError(at('auth_err_generic'));
    } finally {
        els.submitBtn.disabled = false;
    }
}

// ============================================
// SESSION STATE
// ============================================
function setLoggedInState(user) {
    currentUser = user;
    const els = getAuthElements();
    if (!els.userInfoBar) return;

    els.userInfoBar.style.display = 'flex';
    els.loginPrompt.style.display = 'none';
    els.userEmail.textContent = user.email;
    els.logoutBtn.textContent = at('auth_logout');

    // Show watchlist tab
    if (els.watchlistTab) {
        els.watchlistTab.style.display = '';
    }

    // Sync language preference
    if (user.preferred_language && typeof switchLanguage === 'function') {
        if (user.preferred_language !== currentLang) {
            // Don't trigger if already matching
        }
    }
}

function setLoggedOutState() {
    currentUser = null;
    const els = getAuthElements();
    if (!els.userInfoBar) return;

    els.userInfoBar.style.display = 'none';
    els.loginPrompt.style.display = '';

    // Hide watchlist tab
    if (els.watchlistTab) {
        els.watchlistTab.style.display = 'none';
    }

    // Update login prompt text
    els.showAuthBtn.textContent = at('auth_login_prompt');
}

async function checkAuth() {
    try {
        const res = await fetch('/api/auth/me', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            setLoggedInState(data.user);
        } else {
            setLoggedOutState();
        }
    } catch {
        setLoggedOutState();
    }
}

async function handleLogout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include',
        });
    } catch (err) {
        console.error('Logout error:', err);
    }
    setLoggedOutState();
}

// ============================================
// LANGUAGE UPDATE HOOK
// ============================================
function updateAuthLanguage() {
    const els = getAuthElements();
    if (!els.modal) return;

    // Update login prompt
    if (els.showAuthBtn) {
        els.showAuthBtn.textContent = at('auth_login_prompt');
    }
    if (els.logoutBtn) {
        els.logoutBtn.textContent = at('auth_logout');
    }
    // Update modal if open
    if (els.modal.style.display !== 'none') {
        updateAuthModalText();
    }
}

// ============================================
// INIT
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    const els = getAuthElements();

    // Open modal
    if (els.showAuthBtn) {
        els.showAuthBtn.addEventListener('click', () => showAuthModal('login'));
    }

    // Close modal
    if (els.closeBtn) {
        els.closeBtn.addEventListener('click', hideAuthModal);
    }
    if (els.modal) {
        els.modal.addEventListener('click', (e) => {
            if (e.target === els.modal) hideAuthModal();
        });
    }

    // Tab switching
    if (els.loginTab) {
        els.loginTab.addEventListener('click', () => {
            authMode = 'login';
            updateAuthModalText();
            els.error.style.display = 'none';
        });
    }
    if (els.signupTab) {
        els.signupTab.addEventListener('click', () => {
            authMode = 'signup';
            updateAuthModalText();
            els.error.style.display = 'none';
        });
    }

    // Form submit
    if (els.form) {
        els.form.addEventListener('submit', handleAuthSubmit);
    }

    // Logout
    if (els.logoutBtn) {
        els.logoutBtn.addEventListener('click', handleLogout);
    }

    // Keyboard: Escape closes modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') hideAuthModal();
    });

    // Check auth on page load
    checkAuth();
});
