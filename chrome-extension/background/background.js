/**
 * Background Service Worker
 * Manages WebSocket connection to Python backend and routes messages to content scripts
 */

let ws = null;
let reconnectDelay = 1000;
const maxReconnectDelay = 30000;
const wsUrl = 'ws://localhost:8765';

// Connect to WebSocket server
function connectWebSocket() {
  console.log('[Background] Connecting to WebSocket server...');

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[Background] ✅ Connected to fact-checker backend');
    reconnectDelay = 1000;

    // Notify popup of connection status
    updateConnectionStatus(true);
  };

  ws.onmessage = (event) => {
    console.log('[Background] Received message:', event.data);

    try {
      const message = JSON.parse(event.data);

      // Route message to active tab's content script
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]) {
          chrome.tabs.sendMessage(tabs[0].id, message, (response) => {
            if (chrome.runtime.lastError) {
              console.log('[Background] Content script not ready:', chrome.runtime.lastError.message);
            }
          });
        }
      });
    } catch (error) {
      console.error('[Background] Error parsing message:', error);
    }
  };

  ws.onerror = (error) => {
    console.log('[Background] ⚠️ WebSocket connection failed (backend not running?)');
    updateConnectionStatus(false);
  };

  ws.onclose = () => {
    console.log('[Background] 🔌 Connection closed. Will retry in', reconnectDelay / 1000, 'seconds...');
    updateConnectionStatus(false);
    reconnect();
  };
}

// Reconnect with exponential backoff
function reconnect() {
  setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
    connectWebSocket();
  }, reconnectDelay);
}

// Update connection status in storage
function updateConnectionStatus(connected) {
  chrome.storage.local.set({ connected: connected });
}

// Start connection when extension loads
connectWebSocket();

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getConnectionStatus') {
    sendResponse({
      connected: ws && ws.readyState === WebSocket.OPEN
    });
  } else if (request.action === 'reconnect') {
    if (ws) {
      ws.close();
    }
    connectWebSocket();
    sendResponse({ success: true });
  }
  return true;
});

console.log('[Background] Service worker initialized');
