/**
 * 간단한 세션 기반 인증 매니저
 */
const AuthManager = (() => {
    const INACTIVITY_LIMIT_MS = 60 * 60 * 1000; // 1 hour
    const activityEvents = ['mousemove', 'keydown', 'click', 'touchstart', 'scroll'];
    const ADMIN_ALIAS = 'admin';
    const ADMIN_EMAIL = 'admin@system.local';

    const DEFAULT_TAB_TARGET = 'dashboard-view';
    let inactivityTimer = null;
    let initialized = false;
    let unlocked = false;
    let allowedTabs = ['*'];
    window.__allowedTabs = allowedTabs;

    const refs = {
        loginScreen: null,
        appShell: null,
        loginForm: null,
        email: null,
        password: null,
        loginButton: null,
        status: null,
        userPill: null,
        userName: null,
        userAvatar: null,
        logoutButton: null
    };

    function init() {
        if (initialized) {
            return;
        }

        cacheDom();
        bindEvents();
        observeActivity();
        syncSession();
        initialized = true;
    }

    function cacheDom() {
        refs.loginScreen = document.getElementById('login-screen');
        refs.appShell = document.getElementById('app-shell');
        refs.loginForm = document.getElementById('login-form');
        refs.email = document.getElementById('login-email');
        refs.password = document.getElementById('login-password');
        refs.loginButton = document.querySelector('.login-btn');
        refs.status = document.getElementById('login-status');
        refs.userPill = document.getElementById('user-pill');
        refs.userName = document.getElementById('user-name-display');
        refs.userAvatar = document.getElementById('user-avatar');
        refs.logoutButton = document.getElementById('logout-btn');
    }

    function bindEvents() {
        if (refs.loginForm) {
            refs.loginForm.addEventListener('submit', handleLoginSubmit);
        }
        if (refs.logoutButton) {
            refs.logoutButton.addEventListener('click', handleLogoutClick);
        }

        window.addEventListener('auth:required', () => {
            if (unlocked) {
                performLogout('세션이 만료되었습니다. 다시 로그인해주세요.');
            }
        });
    }

    function observeActivity() {
        activityEvents.forEach(eventName => {
            document.addEventListener(eventName, () => {
                if (unlocked) {
                    resetInactivityTimer();
                }
            }, { passive: true });
        });
    }

    async function syncSession() {
        setStatus('세션 상태를 확인하는 중입니다...');
        try {
            const session = await api.getSession();
            if (session.authenticated) {
                unlockApp(session.user, session.expires_in);
                setStatus('세션이 복원되었습니다.', 'success');
            } else {
                lockApp('접속을 위해 로그인하세요.');
            }
        } catch (error) {
            // API 오류 시 로그인 화면 표시
            console.warn('Session check failed:', error.message);
            lockApp('접속을 위해 로그인하세요.');
        }
    }

    async function handleLoginSubmit(event) {
        event.preventDefault();
        const rawEmail = (refs.email && refs.email.value ? refs.email.value : '').trim();
        const password = refs.password && refs.password.value ? refs.password.value : '';
        const normalizedEmail = normalizeLoginIdentifier(rawEmail);

        if (!normalizedEmail || !password) {
            setStatus('이메일과 비밀번호를 입력해주세요.', 'error');
            return;
        }

        if (!isAdminAlias(rawEmail) && !isEmailLike(rawEmail)) {
            setStatus('유효한 이메일 주소를 입력해주세요.', 'error');
            return;
        }

        toggleFormDisabled(true);
        setStatus('인증 중입니다...');

        try {
            const result = await api.login(normalizedEmail, password);
            setStatus('로그인되었습니다.', 'success');
            unlockApp(result.user, result.expires_in);
            if (refs.loginForm) {
                refs.loginForm.reset();
            }
        } catch (error) {
            setStatus(error.message || '로그인에 실패했습니다.', 'error');
        } finally {
            toggleFormDisabled(false);
        }
    }

    function toggleFormDisabled(disabled) {
        if (refs.email) refs.email.disabled = disabled;
        if (refs.password) refs.password.disabled = disabled;
        if (refs.loginButton) refs.loginButton.disabled = disabled;
    }

    async function handleLogoutClick(event) {
        event?.preventDefault();
        await performLogout('로그아웃되었습니다.');
    }

    async function performLogout(message) {
        try {
            await api.logout();
        } catch (error) {
            console.warn('로그아웃 요청 실패:', error);
        }
        lockApp(message);
    }

    function lockApp(message) {
        const wasUnlocked = unlocked;
        unlocked = false;
        stopInactivityTimer();

        if (refs.appShell) {
            refs.appShell.classList.add('locked');
        }
        if (refs.loginScreen) {
            refs.loginScreen.classList.remove('hidden');
        }
        if (refs.userPill) {
            refs.userPill.classList.remove('visible');
        }

        updateAllowedTabs(['*']);
        setBodyUserRole('guest');
        applyTabVisibility(null);
        setStatus(message || '');

        if (wasUnlocked) {
            window.dispatchEvent(new CustomEvent('auth:locked'));
        }
    }

    function unlockApp(user, expiresIn) {
        const email = (user && user.email) ? user.email : '';
        const username = (user && user.username) ? user.username : (email.split('@')[0] || 'controller');
        const displayLabel = email || username;
        const wasUnlocked = unlocked;
        unlocked = true;

        if (refs.appShell) {
            refs.appShell.classList.remove('locked');
        }
        if (refs.loginScreen) {
            refs.loginScreen.classList.add('hidden');
        }
        if (refs.userPill) {
            refs.userPill.classList.add('visible');
        }
        if (refs.userName) {
            refs.userName.textContent = displayLabel;
        }
        if (refs.userAvatar) {
            const avatarSeed = email || username;
            refs.userAvatar.textContent = avatarSeed.slice(0, 2).toUpperCase();
        }

        const resolvedRole = resolveUserRole(user);
        setBodyUserRole(resolvedRole);
        updateAllowedTabs(user && user.allowed_tabs ? user.allowed_tabs : ['*']);
        applyTabVisibility(user);
        setStatus('');
        resetInactivityTimer();

        if (!wasUnlocked) {
            window.dispatchEvent(new CustomEvent('auth:ready', {
                detail: { user, expiresIn, allowedTabs }
            }));
        }
    }

    function setStatus(message, state) {
        if (!refs.status) return;
        refs.status.textContent = message || '';
        refs.status.classList.remove('is-error', 'is-success');
        if (state === 'error') {
            refs.status.classList.add('is-error');
        } else if (state === 'success') {
            refs.status.classList.add('is-success');
        }
    }

    function updateAllowedTabs(tabs) {
        if (Array.isArray(tabs) && tabs.length) {
            allowedTabs = tabs;
        } else {
            allowedTabs = ['*'];
        }
        window.__allowedTabs = allowedTabs;
    }

    function resetInactivityTimer() {
        if (!unlocked) {
            return;
        }
        stopInactivityTimer();
        inactivityTimer = setTimeout(handleInactivityTimeout, INACTIVITY_LIMIT_MS);
    }

    function stopInactivityTimer() {
        if (inactivityTimer) {
            clearTimeout(inactivityTimer);
            inactivityTimer = null;
        }
    }

    async function handleInactivityTimeout() {
        await performLogout('1시간 동안 활동이 없어 자동으로 로그아웃되었습니다.');
    }

    function isAdminAlias(value) {
        return (value || '').trim().toLowerCase() === ADMIN_ALIAS;
    }

    function normalizeLoginIdentifier(value) {
        const trimmed = (value || '').trim();
        if (!trimmed) {
            return '';
        }
        if (isAdminAlias(trimmed)) {
            return ADMIN_EMAIL;
        }
        return trimmed;
    }

    function isEmailLike(value) {
        const target = (value || '').trim();
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(target);
    }

    function applyTabVisibility(user) {
        const aircraftTabBtn = document.getElementById('aircraft-tab-btn');
        const aircraftView = document.getElementById('aircraft-view');
        const defaultTabBtn = document.querySelector(`.nav-tab[data-target="${DEFAULT_TAB_TARGET}"]`);
        const userRole = resolveUserRole(user);
        const isAdminUser = userRole === 'admin';
        const shouldShowAircraft = true; // 모든 사용자에게 공개

        if (aircraftTabBtn) {
            const isCurrentlyHidden = aircraftTabBtn.classList.contains('is-hidden');
            aircraftTabBtn.classList.toggle('is-hidden', !shouldShowAircraft);
            if (!shouldShowAircraft && !isCurrentlyHidden && aircraftTabBtn.classList.contains('active') && defaultTabBtn) {
                defaultTabBtn.click();
            }
        }

        if (aircraftView) {
            if (shouldShowAircraft) {
                aircraftView.style.display = '';
            } else {
                aircraftView.classList.remove('active');
                aircraftView.style.display = 'none';
            }
        }
    }

    function setBodyUserRole(role) {
        if (document && document.body) {
            document.body.setAttribute('data-user-role', role || 'guest');
        }
    }

    function resolveUserRole(user) {
        if (!user) {
            return 'guest';
        }
        if (user.role) {
            return user.role;
        }
        if (user.email && user.email.toLowerCase() === ADMIN_EMAIL) {
            return 'admin';
        }
        return 'user';
    }

    return {
        init
    };
})();

document.addEventListener('DOMContentLoaded', () => AuthManager.init());
