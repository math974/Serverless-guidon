/** @format */

// Client WebSocket pour recevoir les événements Pub/Sub du backend Flask

export function listenForCanvasDrawEvents() {
	const socket = new WebSocket('ws://localhost:5000/socket.io/?EIO=4&transport=websocket');

	socket.addEventListener('open', () => {
	});

	socket.addEventListener('message', (event) => {
		try {
			const data = JSON.parse(event.data);
			if (data.data) {
				// Ici, tu peux déclencher une action sur le canvas
			}
		} catch (e) {
			// Certains messages ne sont pas du JSON (protocoles Socket.IO)
		}
	});

	socket.addEventListener('close', () => {
	});

	socket.addEventListener('error', (err) => {
		console.error('Erreur WebSocket:', err);
	});
}
