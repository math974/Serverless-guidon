// Utility functions for canvas application

function normalizeColorValue(color) {
    if (typeof color === 'string') {
        const upper = color.toUpperCase();
        if (/^#[0-9A-F]{6}$/.test(upper)) {
            return upper;
        }
    }
    return DEFAULT_COLOR;
}

function getSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    const urlSession = urlParams.get('session');

    if (urlSession) {
        localStorage.setItem('guidon_session', urlSession);
        const newUrl = window.location.pathname + (window.location.search.replace(/[?&]session=[^&]*/, '').replace(/^\?/, '') || '');
        window.history.replaceState({}, '', newUrl);
        return urlSession;
    }
    const storedSession = localStorage.getItem('guidon_session');
    if (storedSession) {
        return storedSession;
    }

    if (typeof window.SESSION_ID !== 'undefined' && window.SESSION_ID) {
        localStorage.setItem('guidon_session', window.SESSION_ID);
        return window.SESSION_ID;
    }

    return '';
}

async function verifySession(sessionId) {
    if (!sessionId) {
        return false;
    }

    try {
        const response = await fetch(`${API.GATEWAY_BASE_URL}/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({ session_id: sessionId })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.valid === true) {
                return true;
            } else {
                localStorage.removeItem('guidon_session');
                return false;
            }
        } else if (response.status === 401) {
            localStorage.removeItem('guidon_session');
            return false;
        }
        return false;
    } catch (error) {
        console.error('Error verifying session:', error);
        return false;
    }
}

async function loadUserInfo() {
    try {
        const sessionId = getSessionId();
        if (!sessionId) {
            return;
        }

        const response = await fetch(`${API.GATEWAY_BASE_URL}/auth/user`, {
            method: 'GET',
            headers: {
                'X-Session-ID': sessionId
            }
        });

        if (response.ok) {
            const data = await response.json();

            if (data.user_id || data.user) {
                const user = data.user || data;
                CanvasState.userData = {
                    id: user.user_id || user.id,
                    username: user.username || 'web-user',
                    avatar: user.avatar || null
                };
            }
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

function getUserData() {
    if (!CanvasState.userData) {
        return null;
    }
    return CanvasState.userData;
}

function updateUserActivity() {
    CanvasState.lastUserActivity = Date.now();
}

