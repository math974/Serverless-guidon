// Canvas configuration and global state
const PIXEL_SIZE = 10;
const DEFAULT_COLOR = '#FFFFFF';
const AUTO_REFRESH_INTERVAL = 45 * 1000; // 45 seconds
const USER_ACTIVITY_TIMEOUT = 5 * 1000; // 5 seconds

// Global state
const CanvasState = {
    canvasSize: null,
    canvasData: [],
    currentZoom: 1,
    selectedColor: '#FF0000',
    userData: null,
    autoRefreshTimer: null,
    lastUserActivity: Date.now(),
    isDrawing: false,
    pendingDraws: new Map(),

    // DOM elements
    canvas: null,
    ctx: null,
    colorPicker: null,
    colorInput: null,
    xInput: null,
    yInput: null
};

// API configuration
const API = {
    GATEWAY_BASE_URL: typeof window.GATEWAY_URL !== 'undefined' ? window.GATEWAY_URL : window.location.origin,
    WEBHOOK_URL: typeof window.WEBHOOK_URL !== 'undefined' ? window.WEBHOOK_URL : null
};

const DiscordAPI = {
    BASE_URL: 'https://discord.com',
    API_BASE_URL: 'https://discord.com/api/v10',
    CDN_BASE_URL: 'https://cdn.discordapp.com',
    AVATAR_URL: 'https://cdn.discordapp.com/avatars/',
    EMBED_AVATAR_URL: 'https://cdn.discordapp.com/embed/avatars/',
};
