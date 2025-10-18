/**
 * Popup Script
 * Extension popup UI logic
 */

// DOM Elements
const connectionStatus = document.getElementById('connection-status');
const reconnectBtn = document.getElementById('reconnect-btn');
const overlayEnabled = document.getElementById('overlay-enabled');
const autoScroll = document.getElementById('auto-scroll');

// Check connection status
function updateConnectionStatus() {
  chrome.runtime.sendMessage({ action: 'getConnectionStatus' }, (response) => {
    if (response && response.connected) {
      connectionStatus.textContent = 'Connected';
      connectionStatus.className = 'status-badge status-connected';
    } else {
      connectionStatus.textContent = 'Disconnected';
      connectionStatus.className = 'status-badge status-disconnected';
    }
  });
}

// Reconnect button
reconnectBtn.addEventListener('click', () => {
  reconnectBtn.textContent = 'Connecting...';
  reconnectBtn.disabled = true;

  chrome.runtime.sendMessage({ action: 'reconnect' }, () => {
    setTimeout(() => {
      reconnectBtn.textContent = 'Reconnect';
      reconnectBtn.disabled = false;
      updateConnectionStatus();
    }, 1000);
  });
});

// Load settings
function loadSettings() {
  chrome.storage.local.get(['overlayEnabled', 'autoScroll'], (result) => {
    overlayEnabled.checked = result.overlayEnabled !== false;
    autoScroll.checked = result.autoScroll !== false;
  });
}

// Save settings
overlayEnabled.addEventListener('change', () => {
  chrome.storage.local.set({ overlayEnabled: overlayEnabled.checked });
});

autoScroll.addEventListener('change', () => {
  chrome.storage.local.set({ autoScroll: autoScroll.checked });
});

// Initialize
updateConnectionStatus();
loadSettings();

// Update status every 3 seconds
setInterval(updateConnectionStatus, 3000);
