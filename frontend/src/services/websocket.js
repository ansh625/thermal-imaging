class WebSocketService {
  constructor() {
    this.connections = new Map();
    this.reconnectAttempts = new Map();
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
  }

  connect(type, id, onMessage, onError) {
    const key = `${type}_${id}`;
    
    if (this.connections.has(key)) {
      console.log(`WebSocket already connected: ${key}`);
      return this.connections.get(key);
    }

    const wsUrl = type === 'video' 
      ? `ws://localhost:8000/ws/video/${id}`
      : `ws://localhost:8000/ws/updates/${id}`;

    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log(`WebSocket connected: ${key}`);
      this.reconnectAttempts.set(key, 0);
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
      console.error(`WebSocket error: ${key}`, error);
      if (onError) onError(error);
    };

    ws.onclose = () => {
      console.log(`WebSocket closed: ${key}`);
      this.connections.delete(key);
      this.handleReconnect(type, id, onMessage, onError);
    };

    this.connections.set(key, ws);
    return ws;
  }

  handleReconnect(type, id, onMessage, onError) {
    const key = `${type}_${id}`;
    const attempts = this.reconnectAttempts.get(key) || 0;

    if (attempts < this.maxReconnectAttempts) {
      console.log(`Reconnecting ${key} (attempt ${attempts + 1})`);
      this.reconnectAttempts.set(key, attempts + 1);
      
      setTimeout(() => {
        this.connect(type, id, onMessage, onError);
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
      ws.close();
      this.connections.delete(key);
      this.reconnectAttempts.delete(key);
    }
  }

  disconnectAll() {
    this.connections.forEach((ws, key) => {
      ws.close();
    });
    this.connections.clear();
    this.reconnectAttempts.clear();
  }
}

export const websocketService = new WebSocketService();