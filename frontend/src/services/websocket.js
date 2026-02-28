class WebSocketService {
  constructor() {
    this.connections = new Map();
    this.reconnectAttempts = new Map();
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.pingIntervals = new Map();
    this.intentionalDisconnects = new Set();
  }

  connect(type, id, onMessage, onError, onOpen, onClose) {
    const key = `${type}_${id}`;
    this.intentionalDisconnects.delete(key);

    if (this.connections.has(key)) {
      const existingWs = this.connections.get(key);

      // If socket is still connecting or open, reuse it
      if (
        existingWs.readyState === WebSocket.OPEN ||
        existingWs.readyState === WebSocket.CONNECTING
      ) {
        console.log(`WebSocket already active: ${key}`);
        return existingWs;
      }

      // If closed, remove and create new
      this.connections.delete(key);
    }

    const wsUrl =
      type === 'video'
        ? `ws://localhost:8000/ws/video/${id}`
        : `ws://localhost:8000/ws/updates/${id}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`WebSocket connected: ${key}`);
      this.reconnectAttempts.set(key, 0);
      if (onOpen) {
        onOpen();
      }
      // Start keep-alive ping every 30 seconds
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
      this.pingIntervals.set(key, pingInterval);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('WebSocket message parse error:', error);
      }
    };

    ws.onerror = (error) => {
      if (ws.readyState !== WebSocket.OPEN) {
        return; // Ignore early connection errors
      }
      console.error(`WebSocket error: ${key}`, error);
      if (onError) onError(error);
    };

    ws.onclose = () => {
      console.log(`WebSocket closed: ${key}`);
      if (onClose) {
        onClose();
      }
      this.connections.delete(key);
      // Clear ping interval
      if (this.pingIntervals.has(key)) {
        clearInterval(this.pingIntervals.get(key));
        this.pingIntervals.delete(key);
      }

      if (this.intentionalDisconnects.has(key)) {
        this.intentionalDisconnects.delete(key);
        this.reconnectAttempts.delete(key);
        return;
      }

      this.handleReconnect(type, id, onMessage, onError, onOpen, onClose);
    };

    this.connections.set(key, ws);
    return ws;
  }

  handleReconnect(type, id, onMessage, onError, onOpen, onClose) {
    const key = `${type}_${id}`;
    const attempts = this.reconnectAttempts.get(key) || 0;

    if (attempts < this.maxReconnectAttempts) {
      console.log(`Reconnecting ${key} (attempt ${attempts + 1})`);
      this.reconnectAttempts.set(key, attempts + 1);

      setTimeout(() => {
        this.connect(type, id, onMessage, onError, onOpen, onClose);
      }, this.reconnectDelay);
    } else {
      console.error(`Max reconnect attempts reached for ${key}`);
      this.reconnectAttempts.delete(key);
    }
  }

  send(type, id, message) {
    const key = `${type}_${id}`;
    const ws = this.connections.get(key);

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  disconnect(type, id) {
    const key = `${type}_${id}`;
    const ws = this.connections.get(key);
    if (ws) {
      this.intentionalDisconnects.add(key);
      ws.close();
    }
  }

  disconnectAll() {
    this.connections.forEach((ws, key) => {
      this.intentionalDisconnects.add(key);
      ws.close();
    });
  }
}

export const websocketService = new WebSocketService();
