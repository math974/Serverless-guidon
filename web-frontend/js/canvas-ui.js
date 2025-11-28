// UI helper functions

function showLoading(show) {
    const loading = document.getElementById('loading');
    if (loading) {
        loading.classList.toggle('hidden', !show);
    }
}

let notificationTimeout = null;

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    if (!notification) {
        return;
    }

    if (notificationTimeout) {
        clearTimeout(notificationTimeout);
        notificationTimeout = null;
    }

    notification.style.display = 'none';

    setTimeout(() => {
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.style.display = 'block';

        notificationTimeout = setTimeout(() => {
            if (notification) {
                notification.style.display = 'none';
            }
            notificationTimeout = null;
        }, 3000);
    }, 50);
}

function addActivity(message) {
    const feed = document.getElementById('activityFeed');
    if (!feed) {
        return;
    }

    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <div>${message}</div>
        <div class="time">${new Date().toLocaleTimeString()}</div>
    `;

    feed.insertBefore(item, feed.firstChild);

    while (feed.children.length > 10) {
        feed.removeChild(feed.lastChild);
    }
}

function setColor(color, event) {
    if (!CanvasState.colorPicker || !CanvasState.colorInput) {
        console.error('[canvas-ui] Cannot set color - colorPicker or colorInput not initialized');
        return;
    }

    CanvasState.selectedColor = color;
    CanvasState.colorPicker.value = color;
    CanvasState.colorInput.value = color;

    document.querySelectorAll('.preset-color').forEach(el => {
        el.classList.remove('active');
    });

    if (event && event.target) {
        event.target.classList.add('active');
    }
}

function getMaxZoom() {
    return 50;
}

function zoomIn() {
    const maxZoom = getMaxZoom();
    CanvasState.currentZoom = Math.min(CanvasState.currentZoom + 0.5, maxZoom);
    updateZoom();
}

function zoomOut() {
    CanvasState.currentZoom = Math.max(CanvasState.currentZoom - 0.5, 0.5);
    updateZoom();
}

function updateZoom(mouseX = null, mouseY = null) {
    if (!CanvasState.canvas) {
        console.error('[canvas-ui] Cannot update zoom - canvas not initialized');
        return;
    }

    const maxZoom = getMaxZoom();
    if (CanvasState.currentZoom > maxZoom) {
        CanvasState.currentZoom = maxZoom;
    }

    if (mouseX !== null && mouseY !== null) {
        const rect = CanvasState.canvas.getBoundingClientRect();
        const canvasX = mouseX - rect.left;
        const canvasY = mouseY - rect.top;

        const originX = (canvasX / rect.width) * 100;
        const originY = (canvasY / rect.height) * 100;

        CanvasState.canvas.style.transformOrigin = `${originX}% ${originY}%`;
    } else {
        CanvasState.canvas.style.transformOrigin = 'center center';
    }

    CanvasState.canvas.style.transform = `scale(${CanvasState.currentZoom})`;

    const zoomLevel = document.getElementById('zoomLevel');
    if (zoomLevel) {
        zoomLevel.textContent = `${Math.round(CanvasState.currentZoom * 100)}%`;
    }
}

function exportCanvas() {
    if (!CanvasState.canvas) {
        console.error('[canvas-ui] Cannot export - canvas not initialized');
        return;
    }

    const link = document.createElement('a');
    link.download = `canvas-${Date.now()}.png`;
    link.href = CanvasState.canvas.toDataURL();
    link.click();
}

