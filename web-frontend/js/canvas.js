// Main canvas application
// Note: canvas-config.js, canvas-utils.js, canvas-ui.js, and canvas-render.js must be loaded first

document.addEventListener('DOMContentLoaded', async () => {
    CanvasState.canvas = document.getElementById('canvas');
    if (!CanvasState.canvas) {
        console.error('[canvas.js] Canvas element not found!');
        return;
    }
    CanvasState.ctx = CanvasState.canvas.getContext('2d');
    CanvasState.colorPicker = document.getElementById('colorPicker');
    CanvasState.colorInput = document.getElementById('colorInput');
    CanvasState.xInput = document.getElementById('xInput');
    CanvasState.yInput = document.getElementById('yInput');

    if (!CanvasState.ctx || !CanvasState.colorPicker || !CanvasState.colorInput || !CanvasState.xInput || !CanvasState.yInput) {
        console.error('[canvas.js] Some required DOM elements are missing:', {
            canvas: !!CanvasState.canvas,
            ctx: !!CanvasState.ctx,
            colorPicker: !!CanvasState.colorPicker,
            colorInput: !!CanvasState.colorInput,
            xInput: !!CanvasState.xInput,
            yInput: !!CanvasState.yInput
        });
        return;
    }

    const sessionId = getSessionId();
    if (!sessionId) {
        window.location.href = '/login';
        return;
    }

    const isValid = await verifySession(sessionId);
    if (!isValid) {
        localStorage.removeItem('guidon_session');
        window.location.href = '/login';
        return;
    }

    await loadUserInfo();
    updateUserDisplay();

    setupEventListeners();

    await loadCanvas();

    startAutoRefresh();

    window.addEventListener('resize', () => {
        if (CanvasState.canvas && CanvasState.canvasSize) {
            updateZoom();
        }
    });

    const canvasWrapper = CanvasState.canvas?.closest('.canvas-wrapper');
    if (canvasWrapper) {
        canvasWrapper.addEventListener('wheel', (e) => {
            try {
                if (!CanvasState.canvasSize) {
            return;
        }
                e.preventDefault();

                const delta = e.deltaY;
                const zoomStep = 0.1;

                const canvasRect = CanvasState.canvas.getBoundingClientRect();
                const mouseX = e.clientX;
                const mouseY = e.clientY;
                if (delta < 0) {
                    const maxZoom = getMaxZoom();
                    CanvasState.currentZoom = Math.min(CanvasState.currentZoom + zoomStep, maxZoom);
            } else {
                    CanvasState.currentZoom = Math.max(CanvasState.currentZoom - zoomStep, 0.5);
                }

                updateZoom(mouseX, mouseY);
                updateUserActivity();
    } catch (error) {
                console.error('[canvas.js] Error in canvas wrapper wheel handler:', error);
            }
        }, { passive: false });
    }

            window.drawPixel = drawPixel;
            window.loadCanvas = loadCanvas;
            window.exportCanvas = exportCanvas;
            window.zoomIn = zoomIn;
            window.zoomOut = zoomOut;
            window.setColor = setColor;
            window.closePixelInfoModal = closePixelInfoModal;
            window.logout = logout;

            const modal = document.getElementById('pixelInfoModal');
            if (modal) {
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        closePixelInfoModal();
                    }
                });
            }
});

function setupEventListeners() {
    if (!CanvasState.colorPicker || !CanvasState.colorInput || !CanvasState.canvas || !CanvasState.xInput || !CanvasState.yInput) {
        console.error('[canvas.js] Cannot setup event listeners - DOM elements not initialized');
            return;
        }

    CanvasState.colorPicker.addEventListener('change', (e) => {
        try {
            CanvasState.selectedColor = e.target.value.toUpperCase();
            if (CanvasState.colorInput) {
                CanvasState.colorInput.value = CanvasState.selectedColor;
            }
            updateUserActivity();
        } catch (error) {
            console.error('[canvas.js] Error in colorPicker change handler:', error);
        }
    });

    CanvasState.colorInput.addEventListener('change', (e) => {
        try {
        const value = e.target.value.toUpperCase();
        if (/^#[0-9A-F]{6}$/.test(value)) {
                CanvasState.selectedColor = value;
                if (CanvasState.colorPicker) {
                    CanvasState.colorPicker.value = value;
                }
            }
            updateUserActivity();
    } catch (error) {
            console.error('[canvas.js] Error in colorInput change handler:', error);
        }
    });

    CanvasState.canvas.addEventListener('click', (e) => {
        try {
            if (!CanvasState.canvasSize || CanvasState.isDrawing) {
                return;
            }

            const rect = CanvasState.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) / (PIXEL_SIZE * CanvasState.currentZoom));
            const y = Math.floor((e.clientY - rect.top) / (PIXEL_SIZE * CanvasState.currentZoom));

            if (x >= 0 && x < CanvasState.canvasSize && y >= 0 && y < CanvasState.canvasSize) {
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    showPixelInfo(x, y);
        } else {
                    if (CanvasState.xInput) CanvasState.xInput.value = x;
                    if (CanvasState.yInput) CanvasState.yInput.value = y;
                    drawPixel();
        }
            }
            updateUserActivity();
    } catch (error) {
            console.error('[canvas.js] Error in canvas click handler:', error);
        }
    });

    CanvasState.canvas.addEventListener('contextmenu', (e) => {
        try {
            e.preventDefault();
            if (!CanvasState.canvasSize || CanvasState.isDrawing) {
                return;
            }

            const rect = CanvasState.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) / (PIXEL_SIZE * CanvasState.currentZoom));
            const y = Math.floor((e.clientY - rect.top) / (PIXEL_SIZE * CanvasState.currentZoom));

            if (x >= 0 && x < CanvasState.canvasSize && y >= 0 && y < CanvasState.canvasSize) {
                showPixelInfo(x, y);
            }
        } catch (error) {
            console.error('[canvas.js] Error in canvas contextmenu handler:', error);
        }
    });

    CanvasState.canvas.addEventListener('mousemove', (e) => {
        try {
            if (!CanvasState.canvasSize) {
                return;
            }

            const rect = CanvasState.canvas.getBoundingClientRect();
            const x = Math.floor((e.clientX - rect.left) / (PIXEL_SIZE * CanvasState.currentZoom));
            const y = Math.floor((e.clientY - rect.top) / (PIXEL_SIZE * CanvasState.currentZoom));

            if (x >= 0 && x < CanvasState.canvasSize && y >= 0 && y < CanvasState.canvasSize) {
                const coordsDisplay = document.getElementById('coordsDisplay');
                if (coordsDisplay) {
                    coordsDisplay.textContent = `X: ${x}, Y: ${y} - Click to draw`;
                }
            }
        } catch (error) {
            console.error('[canvas.js] Error in canvas mousemove handler:', error);
        }
    });

    CanvasState.canvas.addEventListener('wheel', (e) => {
        try {
            if (!CanvasState.canvasSize) {
                return;
            }

            e.preventDefault(); // Prevent page scroll

            const delta = e.deltaY;
            const zoomStep = 0.1; // Smaller step for smoother zoom

            const mouseX = e.clientX;
            const mouseY = e.clientY;

            if (delta < 0) {
                const maxZoom = getMaxZoom();
                CanvasState.currentZoom = Math.min(CanvasState.currentZoom + zoomStep, maxZoom);
            } else {
                CanvasState.currentZoom = Math.max(CanvasState.currentZoom - zoomStep, 0.5);
            }
            updateZoom(mouseX, mouseY);
            updateUserActivity();
        } catch (error) {
            console.error('[canvas.js] Error in canvas wheel handler:', error);
        }
    }, { passive: false });
}

function startAutoRefresh() {
    if (CanvasState.autoRefreshTimer) {
        clearInterval(CanvasState.autoRefreshTimer);
    }

    CanvasState.autoRefreshTimer = setInterval(async () => {
        const timeSinceActivity = Date.now() - CanvasState.lastUserActivity;

        if (timeSinceActivity < USER_ACTIVITY_TIMEOUT) {
            return;
        }
        try {
            await loadCanvas();
        } catch (error) {
            console.error('[Auto-refresh] Error refreshing canvas:', error);
        }
    }, AUTO_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (CanvasState.autoRefreshTimer) {
        clearInterval(CanvasState.autoRefreshTimer);
        CanvasState.autoRefreshTimer = null;
    }
}

/**
 * Poll for a response with early termination and exponential backoff.
 * Checks immediately before the first delay to minimize latency.
 * Uses exponential backoff to reduce server load and unnecessary requests.
 *
 * @param {string} token - The token to poll for
 * @param {Object} options - Polling options
 * @param {number} options.maxAttempts - Maximum number of polling attempts (default: 30)
 * @param {number} options.initialDelay - Initial delay in ms (default: 200)
 * @param {number} options.maxDelay - Maximum delay in ms (default: 2000)
 * @param {number} options.backoffMultiplier - Multiplier for exponential backoff (default: 1.5)
 * @param {number} options.jitterMax - Maximum jitter in ms to add (default: 100)
 * @param {Function} options.checkResponse - Function to check if response is complete
 * @param {Function} options.onSuccess - Callback when response is received
 * @param {Function} options.onError - Callback when error occurs
 * @returns {Promise<Object|null>} Response data or null if timeout
 */
async function pollWithEarlyTermination(token, options = {}) {
    const {
        maxAttempts = 30,
        initialDelay = 200,
        maxDelay = 2000,
        backoffMultiplier = 1.5,
        jitterMax = 100,
        checkResponse = (data) => data.status !== 'pending' && data.status !== 'processing',
        onSuccess = null,
        onError = null
    } = options;

    // Early termination: Check immediately before first delay
    try {
        const immediateResponse = await fetch(`/response/${token}`);
        if (immediateResponse.status === 200) {
            const data = await immediateResponse.json();
            if (checkResponse(data)) {
                if (onSuccess) {
                    await onSuccess(data);
                }
                return data;
            }
        } else if (immediateResponse.status === 202) {
            // Response pending, continue polling
        } else {
            // Unexpected status, return null
            if (onError) {
                onError(new Error(`Unexpected status: ${immediateResponse.status}`));
            }
            return null;
        }
    } catch (error) {
        console.error('Error in immediate poll check:', error);
        // Continue with polling despite immediate check error
    }

    // Exponential backoff polling
    let delay = initialDelay;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        // Wait with exponential backoff + jitter
        await new Promise(resolve => setTimeout(resolve, delay));

        try {
            const response = await fetch(`/response/${token}`);
            if (response.status === 200) {
                const data = await response.json();
                if (checkResponse(data)) {
                    if (onSuccess) {
                        await onSuccess(data);
                    }
                    return data;
                }
            } else if (response.status === 202) {
                // Response still pending, continue with increased delay
            } else {
                // Unexpected status
                if (onError) {
                    onError(new Error(`Unexpected status: ${response.status}`));
                }
                return null;
            }
        } catch (error) {
            console.error('Error polling for response:', error);
            if (attempt === maxAttempts - 1) {
                if (onError) {
                    onError(error);
                }
                return null;
            }
        }

        // Calculate next delay with exponential backoff
        delay = Math.min(delay * backoffMultiplier, maxDelay);
        // Add jitter to avoid thundering herd problem
        delay += Math.random() * jitterMax;
    }

    // Timeout
    if (onError) {
        onError(new Error('Polling timeout'));
    }
    return null;
}

function enableDrawButton() {
    const drawButton = document.querySelector('button[onclick="drawPixel()"]');
    if (drawButton) {
        drawButton.disabled = false;
        drawButton.style.opacity = '1';
        drawButton.style.cursor = 'pointer';
    }
}

function disableDrawButton() {
    const drawButton = document.querySelector('button[onclick="drawPixel()"]');
    if (drawButton) {
        drawButton.disabled = true;
        drawButton.style.opacity = '0.6';
        drawButton.style.cursor = 'not-allowed';
    }
}

async function loadCanvas(silent = false) {
    if (!silent) {
    showLoading(true);
    }

    try {
        if (!CanvasState.userData) {
            await loadUserInfo();
        }

        const user = getUserData();
        if (!user) {
            showNotification('User information unavailable. Please refresh the page.', 'error');
            showLoading(false);
            return;
        }

        const sessionId = getSessionId();
        const token = 'canvas-state-' + Date.now();

        const response = await fetch(`${API.GATEWAY_BASE_URL}/web/interactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId || ''
            },
            body: JSON.stringify({
                command: 'canvas_state',
                token: token,
                application_id: 'web-client',
                webhook_url: API.WEBHOOK_URL || null,
                user_id: user.id,
                user: {
                    id: user.id,
                    username: user.username,
                    avatar: user.avatar
                }
            })
        });

        if (response.status === 202) {
            await pollForCanvasStateResult(token, silent);
        } else if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                await handleCanvasStateResponse(data, silent);
            } else if (data.status === 'processing') {
                await pollForCanvasStateResult(token, silent);
            } else {
                console.error('Unexpected status in canvas response:', data.status, data);
                showNotification('Failed to load canvas: ' + (data.message || 'Unknown error'), 'error');
            }
        } else {
            const errorText = await response.text();
            console.error('Failed to load canvas:', response.status, errorText);
            throw new Error('Failed to load canvas: ' + response.status);
        }
    } catch (error) {
        console.error('Error loading canvas:', error);
        showNotification('Failed to load canvas', 'error');
    } finally {
        showLoading(false);
    }
}

async function pollForCanvasStateResult(token, silent = false) {
    const result = await pollWithEarlyTermination(token, {
        maxAttempts: 30,
        initialDelay: 200,
        maxDelay: 2000,
        checkResponse: (data) => {
            return data.status === 'success' || data.status === 'error';
        },
        onSuccess: async (data) => {
            if (data.status === 'success') {
                await handleCanvasStateResponse(data, silent);
            } else if (data.status === 'error') {
                showNotification(data.message || 'Failed to load canvas', 'error');
            }
        },
        onError: (error) => {
            console.error('Polling timeout for token:', token, error);
            if (!silent) {
                showNotification('Timeout waiting for canvas state', 'error');
            }
        }
    });

    if (!result && !silent) {
        showNotification('Timeout waiting for canvas state', 'error');
    }
}

async function handleCanvasStateResponse(data, silent = false) {
    const canvasPayload = data.canvas || data.data?.canvas || data.data?.data?.canvas;

    if (!canvasPayload) {
        throw new Error('No canvas payload in response');
    }

    // Store pending draw pixels before overwriting canvasData
    const pendingPixels = new Map();
    if (CanvasState.pendingDraws) {
        for (const [key, pixel] of CanvasState.pendingDraws.entries()) {
            pendingPixels.set(key, pixel);
        }
    }

    let canvasSize = null;
    if (typeof canvasPayload.size === 'number' && canvasPayload.size > 0) {
        canvasSize = canvasPayload.size;
    } else if (typeof canvasPayload.width === 'number' && canvasPayload.width > 0) {
        canvasSize = canvasPayload.width;
    } else if (typeof canvasPayload.canvas_size === 'number' && canvasPayload.canvas_size > 0) {
        canvasSize = canvasPayload.canvas_size;
    }

    if (canvasSize) {
        CanvasState.canvasSize = canvasSize;

        document.title = `Pixel War ${CanvasState.canvasSize}x${CanvasState.canvasSize}`;
        const headerTitle = document.getElementById('canvasTitle');
        if (headerTitle) {
            headerTitle.textContent = `Pixel War ${CanvasState.canvasSize}x${CanvasState.canvasSize}`;
        } else {
            const headerH1 = document.querySelector('.header h1');
            if (headerH1) {
                headerH1.innerHTML = `<img src="/assets/epitech.png" alt="Epitech" class="epitech-logo"> Pixel War ${CanvasState.canvasSize}x${CanvasState.canvasSize}`;
            }
        }

        if (CanvasState.canvas) {
            CanvasState.canvas.width = CanvasState.canvasSize * PIXEL_SIZE;
            CanvasState.canvas.height = CanvasState.canvasSize * PIXEL_SIZE;
        }

        if (CanvasState.xInput) {
            CanvasState.xInput.max = CanvasState.canvasSize - 1;
            CanvasState.xInput.setAttribute('max', CanvasState.canvasSize - 1);
        }
        if (CanvasState.yInput) {
            CanvasState.yInput.max = CanvasState.canvasSize - 1;
            CanvasState.yInput.setAttribute('max', CanvasState.canvasSize - 1);
        }

        const xLabel = document.querySelector('label[for="xInput"]');
        if (xLabel) {
            xLabel.textContent = `X Coordinate (0-${CanvasState.canvasSize - 1})`;
        }
        const yLabel = document.querySelector('label[for="yInput"]');
        if (yLabel) {
            yLabel.textContent = `Y Coordinate (0-${CanvasState.canvasSize - 1})`;
        }
    } else {
        console.error('[canvas.js] ERROR: No valid canvas width in response!', canvasPayload);
        showNotification('Error: Canvas size not available', 'error');
        throw new Error('Canvas width not found in response');
    }

    let pixels = canvasPayload.pixels;

    if (!pixels && typeof canvasPayload.state_json === 'string') {
        try {
            pixels = JSON.parse(canvasPayload.state_json);
        } catch (error) {
            console.error('Failed to parse canvas JSON:', error);
        }
    }

    if (!pixels || !Array.isArray(pixels)) {
        console.error('Invalid canvas data in response:', canvasPayload);
        throw new Error('Invalid canvas data');
    }

    const normalized = [];
    for (let y = 0; y < CanvasState.canvasSize; y++) {
        const rowData = pixels[y] || [];
        const row = [];
        for (let x = 0; x < CanvasState.canvasSize; x++) {
            const key = `${x},${y}`;
            if (pendingPixels.has(key)) {
                const pendingPixel = pendingPixels.get(key);
                const age = Date.now() - pendingPixel.timestamp;
                if (age < 10000) {
                    const serverColor = normalizeColorValue(rowData[x] || DEFAULT_COLOR);
                    if (serverColor === normalizeColorValue(pendingPixel.color)) {
                        CanvasState.pendingDraws.delete(key);
                    }
                    row.push(normalizeColorValue(pendingPixel.color));
                    continue;
                } else {
                    CanvasState.pendingDraws.delete(key);
                }
            }
            row.push(normalizeColorValue(rowData[x] || DEFAULT_COLOR));
        }
        normalized.push(row);
    }

    CanvasState.canvasData = normalized;
    renderCanvas();

    const statsPayload = canvasPayload.stats || data.stats || data.data?.stats || null;
    if (statsPayload) {
        updateStatsDisplay(statsPayload);
    } else {
        await loadStats();
    }

    if (!silent) {
        showNotification('Canvas loaded successfully!', 'success');
    }
}

async function drawPixel() {
    if (CanvasState.isDrawing) {
        return;
    }

    if (!CanvasState.xInput || !CanvasState.yInput) {
        console.error('[canvas.js] Cannot draw pixel - input elements not initialized');
        return;
    }

    if (!CanvasState.canvasSize) {
        console.error('[canvas.js] Cannot draw pixel - canvas size not yet loaded');
        showNotification('Canvas not loaded yet. Please wait...', 'error');
        return;
    }

    CanvasState.isDrawing = true;
    disableDrawButton();

    // Stop auto-refresh during draw to prevent race conditions
    stopAutoRefresh();

    updateUserActivity();

    const x = parseInt(CanvasState.xInput.value);
    const y = parseInt(CanvasState.yInput.value);
    const color = CanvasState.selectedColor;

    if (x < 0 || x >= CanvasState.canvasSize || y < 0 || y >= CanvasState.canvasSize) {
        showNotification('Invalid coordinates!', 'error');
        CanvasState.isDrawing = false;
        enableDrawButton();
        return;
    }

    showLoading(true);

    try {
        const sessionId = getSessionId();
        if (!sessionId) {
            showNotification('Not authenticated. Please login.', 'error');
            showLoading(false);
            CanvasState.isDrawing = false;
            enableDrawButton();
            return;
        }

        if (!CanvasState.userData) {
            await loadUserInfo();
        }

        const user = getUserData();
        if (!user) {
            showNotification('User information not available. Please refresh the page.', 'error');
            showLoading(false);
            CanvasState.isDrawing = false;
            enableDrawButton();
            return;
        }

        const token = 'draw-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        let response;
        try {
            response = await fetch(`${API.GATEWAY_BASE_URL}/web/interactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({
                command: 'draw',
                token: token,
                application_id: 'web-client',
                    webhook_url: API.WEBHOOK_URL || null,
                user_id: user.id,
                user: {
                    id: user.id,
                    username: user.username,
                    avatar: user.avatar
                },
                options: [
                    { name: 'x', value: x },
                    { name: 'y', value: y },
                    { name: 'color', value: color }
                ]
            })
        });
        } catch (fetchError) {
            console.error('[canvas.js] Fetch error:', fetchError);
            showNotification('Network error', 'error');
            CanvasState.isDrawing = false;
            enableDrawButton();
            showLoading(false);
            return;
        }

        let needsPolling = false;
        let responseData = {};

        if (response.status === 202) {
            needsPolling = true;
            try {
                responseData = await response.json();
            } catch (e) {
            }
        } else if (response.status === 429) {
            showNotification('Rate limit exceeded! Please wait.', 'error');
            CanvasState.isDrawing = false;
            enableDrawButton();
            showLoading(false);
            return;
        } else if (response.ok) {
            try {
                responseData = await response.json();
                if (responseData.status === 'processing') {
                    needsPolling = true;
                } else if (responseData.status === 'success') {
                    if (!CanvasState.canvasData[y]) CanvasState.canvasData[y] = [];
                    CanvasState.canvasData[y][x] = color;
                renderCanvas();
                showNotification(`Pixel drawn at (${x}, ${y})!`, 'success');
                addActivity(`Drew ${color} at (${x}, ${y})`);

                    await new Promise(resolve => setTimeout(resolve, 1500));
                    try {
                        showLoading(true);
                        await loadCanvas(true);
                        showLoading(false);

                        updateUserActivity();
                        startAutoRefresh();
                    } catch (error) {
                        console.error('[canvas.js] Error reloading canvas after draw:', error);
                        showLoading(false);
                        showNotification('Canvas drawn but failed to refresh. Please reload page.', 'warning');
                    }
                    CanvasState.isDrawing = false;
                    enableDrawButton();
                    showLoading(false);
                    return;
            } else {
                    showNotification(responseData.message || 'Failed to draw pixel', 'error');
                    CanvasState.isDrawing = false;
                    enableDrawButton();
                    showLoading(false);
                    return;
                }
            } catch (jsonError) {
                console.error('[canvas.js] Error parsing JSON:', jsonError);
                showNotification('Invalid response from server', 'error');
                CanvasState.isDrawing = false;
                enableDrawButton();
                showLoading(false);
                return;
            }
        } else {
            const error = await response.json().catch(() => ({}));
            showNotification(error.error || error.message || 'Failed to draw pixel', 'error');
            CanvasState.isDrawing = false;
            enableDrawButton();
            showLoading(false);
            return;
        }

        if (needsPolling) {
            if (!CanvasState.canvasData[y]) CanvasState.canvasData[y] = [];
            const previousColor = CanvasState.canvasData[y][x] || DEFAULT_COLOR;
            CanvasState.canvasData[y][x] = color;

            // Track this pixel as pending
            const key = `${x},${y}`;
            CanvasState.pendingDraws.set(key, { color, timestamp: Date.now() });

            renderCanvas();

            try {
                const result = await pollForDrawResult(token);
                showLoading(false);
                CanvasState.isDrawing = false;
                enableDrawButton();

                if (result && result.success && result.data) {
                    const data = result.data;
                    let isSuccess = false;
                    let isError = false;

                    if (data.status === 'success') {
                        isSuccess = true;
                    } else if (data.status === 'error') {
                        isError = true;
                    } else if (data.type === 4 && data.data && data.data.embeds && Array.isArray(data.data.embeds) && data.data.embeds.length > 0) {
                        const embed = data.data.embeds[0];
                        const title = embed.title || '';
                        const description = embed.description || '';
                        const titleLower = title.toLowerCase();
                        const descLower = description.toLowerCase();

                        if (titleLower.includes('error') || titleLower.includes('failed') ||
                            descLower.includes('error') || descLower.includes('failed') ||
                            descLower.includes('invalid') || descLower.includes('unable')) {
                            isError = true;
                        } else {
                            isSuccess = true;
                        }
                    } else if (data.data && data.data.embeds && Array.isArray(data.data.embeds) && data.data.embeds.length > 0) {
                        isSuccess = true;
                    } else if (data.token) {
                        isSuccess = true;
                    }

                    if (isSuccess) {
                        showNotification(`Pixel drawn successfully at (${x}, ${y})!`, 'success');
                        addActivity(`Drew ${color} at (${x}, ${y})`);

                        setTimeout(async () => {
                            try {
                                await loadCanvas(true);
                                updateUserActivity();
                                startAutoRefresh();
                            } catch (error) {
                                console.error('[canvas.js] Error reloading canvas after draw:', error);
                                showNotification('Canvas drawn but failed to refresh. Please reload page.', 'warning');
                            }
                        }, 3000);
                    } else if (isError) {
                        const key = `${x},${y}`;
                        CanvasState.pendingDraws.delete(key);

                        if (CanvasState.canvasData[y]) {
                            CanvasState.canvasData[y][x] = previousColor;
                            renderCanvas();
                        }
                        const errorMessage = data.message || (data.data?.embeds?.[0]?.description) || 'Failed to draw pixel';
                        showNotification(errorMessage, 'error');
                    }
                } else if (result && result.success) {
                    showNotification(`Pixel drawn successfully at (${x}, ${y})!`, 'success');
                    addActivity(`Drew ${color} at (${x}, ${y})`);

                    setTimeout(async () => {
                        try {
                            await loadCanvas(true);
                            updateUserActivity();
                            startAutoRefresh();
                        } catch (error) {
                            console.error('[canvas.js] Error reloading canvas after draw:', error);
                            showNotification('Canvas drawn but failed to refresh. Please reload page.', 'warning');
                        }
                    }, 3000);
                } else {
                    const key = `${x},${y}`;
                    CanvasState.pendingDraws.delete(key);

                    if (CanvasState.canvasData[y]) {
                        CanvasState.canvasData[y][x] = previousColor;
                        renderCanvas();
                    }
                    showNotification('Failed to draw pixel', 'error');
                }
            } catch (pollError) {
                console.error('[canvas.js] Error in polling:', pollError);
                showLoading(false);
                CanvasState.isDrawing = false;
                enableDrawButton();

                const key = `${x},${y}`;
                CanvasState.pendingDraws.delete(key);

                if (CanvasState.canvasData[y]) {
                    CanvasState.canvasData[y][x] = previousColor;
                    renderCanvas();
                }
                showNotification('Error waiting for draw result', 'error');
            }
        }
    } catch (error) {
        console.error('Error drawing pixel:', error);
        showNotification('Connection error', 'error');
    } finally {
        showLoading(false);
        CanvasState.isDrawing = false;
        enableDrawButton();
    }
}

async function showPixelInfo(x, y) {
    try {
        if (!CanvasState.userData) {
            await loadUserInfo();
        }

        const user = getUserData();
        if (!user) {
            showNotification('User information unavailable', 'error');
            return;
        }

        const sessionId = getSessionId();
        const token = 'pixel-info-' + Date.now();

        showNotification(`Loading pixel info at (${x}, ${y})...`, 'info');

        const response = await fetch(`${API.GATEWAY_BASE_URL}/web/interactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId || ''
            },
            body: JSON.stringify({
                command: 'pixel_info',
                token: token,
                application_id: 'web-client',
                webhook_url: API.WEBHOOK_URL || null,
                user_id: user.id,
                user: {
                    id: user.id,
                    username: user.username,
                    avatar: user.avatar
                },
                options: [
                    { name: 'x', value: x },
                    { name: 'y', value: y }
                ]
            })
        });

        if (response.status === 202) {
            await pollForPixelInfoResult(token);
        } else if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                await handlePixelInfoResponse(data);
            } else if (data.status === 'processing') {
                await pollForPixelInfoResult(token);
            } else {
                showNotification('Failed to load pixel info: ' + (data.message || 'Unknown error'), 'error');
            }
        } else {
            showNotification('Failed to load pixel info', 'error');
        }
    } catch (error) {
        console.error('Error loading pixel info:', error);
        showNotification('Error loading pixel info', 'error');
    }
}

async function pollForPixelInfoResult(token) {
    const result = await pollWithEarlyTermination(token, {
        maxAttempts: 10,
        initialDelay: 200,
        maxDelay: 2000,
        checkResponse: (data) => {
            if (data.status === 'processing') {
                return false;
            }
            return data.status === 'success' ||
                    data.status === 'error' ||
                    (data.type === 4 && data.data && data.data.embeds && Array.isArray(data.data.embeds) && data.data.embeds.length > 0);
        },
        onSuccess: async (data) => {
            if (data.status === 'success' ||
                (data.type === 4 && data.data && data.data.embeds && Array.isArray(data.data.embeds) && data.data.embeds.length > 0)) {
                await handlePixelInfoResponse(data);
            } else if (data.status === 'error') {
                showNotification(data.message || 'Failed to load pixel info', 'error');
            }
        },
        onError: (error) => {
            console.error('Error polling for pixel info:', error);
            showNotification('Timeout waiting for pixel info', 'error');
        }
    });

    if (!result) {
        showNotification('Timeout waiting for pixel info', 'error');
    }
}

function getAvatarUrl(userId, avatarHash = null) {
    if (!userId) {
        return `${DiscordAPI.EMBED_AVATAR_URL}0.png`;
    }
    if (avatarHash) {
        return `${DiscordAPI.AVATAR_URL}${userId}/${avatarHash}.png`;
    }
    const discriminatorNum = parseInt(userId) % 5;
    return `${DiscordAPI.EMBED_AVATAR_URL}${discriminatorNum}.png`;
}

function displayPixelInfoModal(pixelInfo) {
    const modal = document.getElementById('pixelInfoModal');
    const content = document.getElementById('pixelInfoContent');

    if (!modal || !content) {
        showNotification('Error: Modal elements not found', 'error');
        return;
    }

    let html = '';

    if (pixelInfo.coordinates || (pixelInfo.x !== undefined && pixelInfo.y !== undefined)) {
        const coords = pixelInfo.coordinates || `(${pixelInfo.x}, ${pixelInfo.y})`;
        html += `
            <div class="pixel-info-item">
                <span class="pixel-info-label"><i class="fas fa-map-marker-alt"></i> Coordinates</span>
                <span class="pixel-info-value">${coords}</span>
            </div>
        `;
    }

    if (pixelInfo.color) {
        const colorValue = pixelInfo.color.replace(/`/g, '').replace(/#/g, '').trim();
        const colorHex = colorValue.startsWith('#') ? colorValue : `#${colorValue}`;
        html += `
            <div class="pixel-info-item">
                <span class="pixel-info-label"><i class="fas fa-palette"></i> Color</span>
                <span class="pixel-info-value">
                    ${colorHex}
                    <span class="pixel-info-color" style="background-color: ${colorHex};"></span>
                </span>
            </div>
        `;
    }

    if (pixelInfo.drawnBy && pixelInfo.drawnBy !== 'Empty' && pixelInfo.drawnBy !== 'Unknown') {
        const userId = pixelInfo.user_id || pixelInfo.userId;
        const avatarUrl = getAvatarUrl(userId, pixelInfo.avatar);
        html += `
            <div class="pixel-info-item">
                <span class="pixel-info-label"><i class="fas fa-user"></i> Drawn by</span>
                <div class="pixel-info-value">
                    <div class="pixel-info-user">
                        <img src="${avatarUrl}" alt="${pixelInfo.drawnBy}" class="pixel-info-avatar" onerror="this.src='${DiscordAPI.EMBED_AVATAR_URL}0.png'">
                        <span class="pixel-info-username">${pixelInfo.drawnBy}</span>
                    </div>
                </div>
            </div>
        `;
    } else if (pixelInfo.user_id || pixelInfo.userId) {
        const userId = pixelInfo.user_id || pixelInfo.userId;
        const avatarUrl = getAvatarUrl(userId, pixelInfo.avatar);
        html += `
            <div class="pixel-info-item">
                <span class="pixel-info-label"><i class="fas fa-user"></i> Drawn by</span>
                <div class="pixel-info-value">
                    <div class="pixel-info-user">
                        <img src="${avatarUrl}" alt="Unknown User" class="pixel-info-avatar" onerror="this.src='${DiscordAPI.EMBED_AVATAR_URL}0.png'">
                        <span class="pixel-info-username">Unknown User</span>
                    </div>
                </div>
            </div>
        `;
    }

    if (pixelInfo.lastUpdated || pixelInfo.timestamp) {
        const timestamp = pixelInfo.lastUpdated || pixelInfo.timestamp;
        let formattedDate = timestamp;
        try {
            const date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                formattedDate = date.toLocaleString('fr-FR', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }
        } catch (e) {
        }
        html += `
            <div class="pixel-info-item">
                <span class="pixel-info-label"><i class="fas fa-clock"></i> Last updated</span>
                <span class="pixel-info-value">${formattedDate}</span>
            </div>
        `;
    }

    if (pixelInfo.editCount || pixelInfo.edit_count !== undefined) {
        const editCount = pixelInfo.editCount || pixelInfo.edit_count || 0;
        html += `
            <div class="pixel-info-item">
                <span class="pixel-info-label"><i class="fas fa-edit"></i> Edit count</span>
                <span class="pixel-info-value">${editCount} time${editCount !== 1 ? 's' : ''}</span>
            </div>
        `;
    }

    if (!html) {
        html = '<div class="pixel-info-loading">No information available for this pixel</div>';
    }

    content.innerHTML = html;
    modal.style.display = 'flex';
}

function closePixelInfoModal() {
    const modal = document.getElementById('pixelInfoModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function handlePixelInfoResponse(data) {
    try {
        let pixelInfo = null;

        if (data.pixel_info) {
            pixelInfo = { ...data.pixel_info };
        } else if (data.data?.pixel_info) {
            pixelInfo = { ...data.data.pixel_info };
        } else if (data.type === 4 && data.data && data.data.embeds && data.data.embeds.length > 0) {
            const embed = data.data.embeds[0];
            const fields = embed.fields || [];

            pixelInfo = {
                coordinates: null,
                color: null,
                drawnBy: null,
                lastUpdated: null,
                editCount: null,
                user_id: null,
                userId: null,
                avatar: null
            };

            for (const field of fields) {
                const name = field.name || '';
                const value = field.value || '';

                if (name.includes('Coordinates') || name.includes('Coordinate')) {
                    pixelInfo.coordinates = value.replace(/\*\*/g, '').trim();
                } else if (name.includes('Color')) {
                    pixelInfo.color = value.replace(/`/g, '').trim();
                } else if (name.includes('Drawn by') || name.includes('Drawn by')) {
                    pixelInfo.drawnBy = value.replace(/\*\*/g, '').trim();
                } else if (name.includes('Last updated') || name.includes('Last updated')) {
                    pixelInfo.lastUpdated = value.trim();
                } else if (name.includes('Edit count')) {
                    pixelInfo.editCount = value.replace(/\*\*/g, '').trim();
                }
            }

            if (embed.author) {
                const authorUrl = embed.author.icon_url || embed.author.url || '';
                const match = authorUrl.match(/avatars\/(\d+)\/([^\/]+)/);
                if (match) {
                    pixelInfo.user_id = match[1];
                    pixelInfo.userId = match[1];
                    pixelInfo.avatar = match[2];
                }
            }
        }
        if (!pixelInfo) {
            showNotification('No pixel information available', 'error');
            return;
        }
        if (pixelInfo.user_id && !pixelInfo.userId) {
            pixelInfo.userId = pixelInfo.user_id;
        }
        displayPixelInfoModal(pixelInfo);
        } catch (error) {
        console.error('Error handling pixel info response:', error);
        showNotification('Error parsing pixel information', 'error');
        }
}

async function loadStats() {
    try {
        if (!CanvasState.userData) {
            await loadUserInfo();
        }

        const user = getUserData();
        if (!user) {
            return;
        }

        const token = 'stats-' + Date.now();
        const response = await fetch(`${API.GATEWAY_BASE_URL}/web/interactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                command: 'stats',
                token: token,
                application_id: 'web-client',
                webhook_url: API.WEBHOOK_URL || null,
                user_id: user.id,
                user: {
                    id: user.id,
                    username: user.username,
                    avatar: user.avatar
                }
            })
        });

        if (response.status === 202) {
            await pollForStatsResult(token);
        } else if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                parseStatsFromResponse(data);
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function pollForStatsResult(token) {
    const result = await pollWithEarlyTermination(token, {
        maxAttempts: 10,
        initialDelay: 200,
        maxDelay: 2000,
        checkResponse: (data) => {
            return data.status === 'success';
        },
        onSuccess: (data) => {
            parseStatsFromResponse(data);
        },
        onError: (error) => {
            console.error('Error polling for stats:', error);
        }
    });
}

function updateStatsDisplay(stats) {
    if (!stats) {
        return;
    }

    const totalPixelsEl = document.getElementById('totalPixels');
    const contributorsEl = document.getElementById('contributors');
    const contributorsListEl = document.getElementById('contributorsList');
    const contributorsListRow = document.getElementById('contributorsListRow');
    const lastUpdateEl = document.getElementById('lastUpdate');

    if (totalPixelsEl && typeof stats.total_pixels !== 'undefined') {
        totalPixelsEl.textContent = stats.total_pixels;
    }

    if (contributorsEl && typeof stats.unique_contributors !== 'undefined') {
        contributorsEl.textContent = stats.unique_contributors;
    }

    if (stats.contributors && Array.isArray(stats.contributors) && stats.contributors.length > 0) {
        if (contributorsListEl && contributorsListRow) {
            contributorsListEl.innerHTML = '';
            stats.contributors.forEach(contributor => {
                const contributorDiv = document.createElement('div');
                contributorDiv.style.display = 'flex';
                contributorDiv.style.alignItems = 'center';
                contributorDiv.style.gap = '0.5rem';
                contributorDiv.style.padding = '0.25rem 0.5rem';
                contributorDiv.style.background = 'var(--bg-tertiary)';
                contributorDiv.style.borderRadius = '12px';
                contributorDiv.style.fontSize = '0.85rem';

                const avatarUrl = contributor.avatar
                    ? `${DiscordAPI.AVATAR_URL}${contributor.id}/${contributor.avatar}.png`
                    : `${DiscordAPI.EMBED_AVATAR_URL}${(parseInt(contributor.id) % 5)}.png`;

                const avatarImg = document.createElement('img');
                avatarImg.src = avatarUrl;
                avatarImg.alt = contributor.username || 'User';
                avatarImg.style.width = '24px';
                avatarImg.style.height = '24px';
                avatarImg.style.borderRadius = '50%';
                avatarImg.style.objectFit = 'cover';

                const usernameSpan = document.createElement('span');
                usernameSpan.textContent = contributor.username || `User ${contributor.id}`;
                usernameSpan.className = 'contributor-username';

                contributorDiv.appendChild(avatarImg);
                contributorDiv.appendChild(usernameSpan);
                contributorsListEl.appendChild(contributorDiv);
            });
            contributorsListRow.style.display = 'block';
        }
    } else if (contributorsListRow) {
        contributorsListRow.style.display = 'none';
    }

    if (lastUpdateEl && stats.last_update) {
        try {
            const date = new Date(stats.last_update);
            if (!isNaN(date.getTime())) {
                const dateStr = date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                });
                const timeStr = date.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    hour12: true
                });
                lastUpdateEl.innerHTML = `${dateStr}<br>${timeStr}`;
            } else {
                lastUpdateEl.textContent = stats.last_update;
            }
        } catch (e) {
            lastUpdateEl.textContent = stats.last_update || 'Never';
        }
    } else if (lastUpdateEl) {
        lastUpdateEl.textContent = 'Never';
    }
}

function parseStatsFromResponse(data) {
    const statsPayload = data.stats || data.canvas?.stats || data.data?.stats || null;
    if (statsPayload) {
        updateStatsDisplay(statsPayload);
        return;
    }

    const embeds = data.data?.embeds || data.data?.data?.embeds || data.embeds || [];
    if (embeds.length > 0 && embeds[0].fields) {
        const fields = embeds[0].fields;
        let totalPixels = 0;
        let contributors = 0;

        for (const field of fields) {
            const name = field.name?.toLowerCase() || '';
            const value = field.value || '';

            if (name.includes('total pixels') || name.includes('pixels drawn') || name.includes('pixels')) {
                const match = value.match(/\d+/);
                totalPixels = match ? parseInt(match[0]) : 0;
            } else if (name.includes('contributors') || name.includes('artists') || name.includes('unique')) {
                const match = value.match(/\d+/);
                contributors = match ? parseInt(match[0]) : 0;
            }
        }

        const totalPixelsEl = document.getElementById('totalPixels');
        const contributorsEl = document.getElementById('contributors');

        if (totalPixelsEl) {
            totalPixelsEl.textContent = totalPixels;
        }

        if (contributorsEl) {
            contributorsEl.textContent = contributors;
        }
    }
}

async function pollForDrawResult(token) {
    let resultData = null;
    let isSuccess = false;
    let isError = false;

    const result = await pollWithEarlyTermination(token, {
        maxAttempts: 30,
        initialDelay: 200,
        maxDelay: 2000,
        checkResponse: (data) => {
            if (data.status === 'processing') {
                return false;
            }

            isSuccess = false;
            isError = false;

            if (data.status === 'success') {
                isSuccess = true;
                resultData = data;
                return true;
            } else if (data.status === 'error') {
                isError = true;
                resultData = data;
                return true;
            } else if (data.type === 4 && data.data && data.data.embeds && Array.isArray(data.data.embeds) && data.data.embeds.length > 0) {
                const embed = data.data.embeds[0];
                const title = embed.title || '';
                const description = embed.description || '';
                const titleLower = title.toLowerCase();
                const descLower = description.toLowerCase();

                if (titleLower.includes('error') || titleLower.includes('failed') ||
                    descLower.includes('error') || descLower.includes('failed') ||
                    descLower.includes('invalid') || descLower.includes('unable')) {
                    isError = true;
                } else if (title === 'Pixel Placed Successfully' ||
                         titleLower.includes('success') || titleLower.includes('placed') ||
                         descLower.includes('successfully placed') ||
                         descLower.includes('successfully') ||
                         descLower.includes('placed')) {
                    isSuccess = true;
                } else {
                    isSuccess = true;
                }
                resultData = data;
                return true;
            } else if (data.data && data.data.embeds && Array.isArray(data.data.embeds) && data.data.embeds.length > 0) {
                isSuccess = true;
                resultData = data;
                return true;
            } else if (data.token) {
                isSuccess = true;
                resultData = data;
                return true;
            }

            return false;
        },
        onSuccess: (data) => {
            // Response already processed in checkResponse
        },
        onError: (error) => {
            console.error('Error polling for draw result:', error);
            showNotification('Timeout waiting for draw result', 'error');
        }
    });

    if (result && resultData) {
        if (isSuccess) {
            return { success: true, data: resultData };
        } else if (isError) {
            const errorMessage = resultData.message || (resultData.data?.embeds?.[0]?.description) || 'Failed to draw pixel';
            showNotification(errorMessage, 'error');
            return { success: false };
        }
    }

    if (!result) {
        showNotification('Timeout waiting for draw result', 'error');
    }
    return { success: false };
}

function updateUserDisplay() {
    const userInfoEl = document.getElementById('userInfo');
    const userAvatarEl = document.getElementById('userAvatar');
    const userUsernameEl = document.getElementById('userUsername');

    if (!userInfoEl || !userAvatarEl || !userUsernameEl) {
        return;
    }

    const user = getUserData();
    if (user && user.username) {
        const avatarUrl = user.avatar
            ? `${DiscordAPI.AVATAR_URL}${user.id}/${user.avatar}.png`
            : `${DiscordAPI.EMBED_AVATAR_URL}${(parseInt(user.id) % 5)}.png`;

        userAvatarEl.src = avatarUrl;
        userAvatarEl.alt = user.username;
        userAvatarEl.onerror = function() {
            this.src = `${DiscordAPI.EMBED_AVATAR_URL}${(parseInt(user.id) % 5)}.png`;
        };

        userUsernameEl.textContent = user.username;
        userInfoEl.style.display = 'flex';

        userInfoEl.onclick = function(e) {
            e.stopPropagation();
            toggleUserMenu();
        };
    } else {
        userInfoEl.style.display = 'none';
    }
}

function toggleUserMenu() {
    const userMenu = document.getElementById('userMenu');
    if (userMenu) {
        const isVisible = userMenu.style.display === 'block';
        userMenu.style.display = isVisible ? 'none' : 'block';

        if (!isVisible) {
            setTimeout(() => {
                document.addEventListener('click', function closeMenu(e) {
                    if (!userMenu.contains(e.target) && !document.getElementById('userInfo').contains(e.target)) {
                        userMenu.style.display = 'none';
                        document.removeEventListener('click', closeMenu);
                    }
                }, { once: true });
            }, 0);
        }
    }
}

async function logout() {
    try {
        const sessionId = getSessionId();
        if (!sessionId) {
            localStorage.removeItem('guidon_session');
            window.location.href = '/login';
            return;
        }

        const response = await fetch(`${API.GATEWAY_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({ session_id: sessionId })
        });

        localStorage.removeItem('guidon_session');

        window.location.href = '/login';
    } catch (error) {
        console.error('Error during logout:', error);
        localStorage.removeItem('guidon_session');
        window.location.href = '/login';
    }
}

