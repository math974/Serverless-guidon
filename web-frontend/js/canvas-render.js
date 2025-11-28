// Canvas rendering functions

function renderCanvas() {
    if (!CanvasState.canvas || !CanvasState.ctx) {
        console.error('[canvas-render] Cannot render - canvas or ctx not initialized');
        return;
    }
    if (!CanvasState.canvasSize) {
        return;
    }

    CanvasState.ctx.clearRect(0, 0, CanvasState.canvas.width, CanvasState.canvas.height);

    for (let y = 0; y < CanvasState.canvasSize; y++) {
        for (let x = 0; x < CanvasState.canvasSize; x++) {
            const color = CanvasState.canvasData[y]?.[x] || DEFAULT_COLOR;
            CanvasState.ctx.fillStyle = color;
            CanvasState.ctx.fillRect(x * PIXEL_SIZE, y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE);
        }
    }

    CanvasState.ctx.strokeStyle = '#00000010';
    CanvasState.ctx.lineWidth = 0.5;
    for (let i = 0; i <= CanvasState.canvasSize; i++) {
        CanvasState.ctx.beginPath();
        CanvasState.ctx.moveTo(i * PIXEL_SIZE, 0);
        CanvasState.ctx.lineTo(i * PIXEL_SIZE, CanvasState.canvas.height);
        CanvasState.ctx.stroke();
    }

    for (let i = 0; i <= CanvasState.canvasSize; i++) {
        CanvasState.ctx.beginPath();
        CanvasState.ctx.moveTo(0, i * PIXEL_SIZE);
        CanvasState.ctx.lineTo(CanvasState.canvas.width, i * PIXEL_SIZE);
        CanvasState.ctx.stroke();
    }
}

async function loadCanvasImage(imageUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => {
            const tempCanvas = document.createElement('canvas');
            tempCanvas.width = CanvasState.canvasSize;
            tempCanvas.height = CanvasState.canvasSize;
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.drawImage(img, 0, 0, CanvasState.canvasSize, CanvasState.canvasSize);

            CanvasState.canvasData = [];
            for (let y = 0; y < CanvasState.canvasSize; y++) {
                const row = [];
                for (let x = 0; x < CanvasState.canvasSize; x++) {
                    const pixelData = tempCtx.getImageData(x, y, 1, 1).data;
                    const hex = '#' + [pixelData[0], pixelData[1], pixelData[2]]
                        .map(c => c.toString(16).padStart(2, '0').toUpperCase())
                        .join('');
                    row.push(hex);
                }
                CanvasState.canvasData.push(row);
            }

            renderCanvas();
            resolve();
        };
        img.onerror = (error) => {
            console.error('Error loading image:', error);
            reject(error);
        };
        img.src = imageUrl;
    });
}

