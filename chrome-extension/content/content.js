/**
 * Content Script
 * Creates live transcript overlay and displays fact-check alerts inline
 */

console.log('[UhmmActually] Content script loaded');

// Transcript data
let transcriptItems = [];
let overlayContainer = null;
let transcriptList = null;

// Create overlay UI
function createOverlay() {
  if (overlayContainer) return;

  overlayContainer = document.createElement('div');
  overlayContainer.id = 'uhmm-actually-overlay';
  overlayContainer.className = 'uhmm-actually-container';

  overlayContainer.innerHTML = `
    <div class="uhmm-header">
      <span class="uhmm-title">📝 Live Transcript</span>
      <div class="uhmm-status">
        <span class="uhmm-status-indicator" id="connection-status"></span>
        <span class="uhmm-status-text" id="status-text">Detected</span>
      </div>
      <button class="uhmm-minimize" title="Minimize">−</button>
    </div>
    <div class="uhmm-transcript-list"></div>
  `;

  document.body.appendChild(overlayContainer);
  transcriptList = overlayContainer.querySelector('.uhmm-transcript-list');

  // Minimize button
  const minimizeBtn = overlayContainer.querySelector('.uhmm-minimize');
  minimizeBtn.addEventListener('click', () => {
    overlayContainer.classList.toggle('minimized');
    minimizeBtn.textContent = overlayContainer.classList.contains('minimized') ? '+' : '−';
  });

  console.log('[UhmmActually] Overlay created');
}

// Add transcript item
function addTranscript(data) {
  const item = {
    id: Date.now() + Math.random(),
    type: 'transcript',
    text: data.text,
    speaker: data.speaker || 'Speaker',
    timestamp: new Date(),
    verdict: null
  };

  transcriptItems.push(item);

  // Keep only last 20 items
  if (transcriptItems.length > 20) {
    transcriptItems.shift();
  }

  renderTranscript();
}

// Add verdict alert (inline with transcript)
function addVerdict(data) {
  // Find matching transcript item
  const matchingItem = transcriptItems
    .slice()
    .reverse()
    .find(item => item.text === data.transcript || item.text.includes(data.claim));

  if (matchingItem && data.status !== 'supported') {
    matchingItem.verdict = {
      status: data.status,
      claim: data.claim,
      confidence: data.confidence,
      rationale: data.rationale,
      evidenceUrl: data.evidence_url
    };
    renderTranscript();
  }
}

// Render transcript list
function renderTranscript() {
  if (!transcriptList) return;

  transcriptList.innerHTML = '';

  if (transcriptItems.length === 0) {
    transcriptList.innerHTML = `
      <div class="uhmm-empty">
        <p>Waiting for speech...</p>
      </div>
    `;
    return;
  }

  transcriptItems.forEach(item => {
    const itemEl = document.createElement('div');
    itemEl.className = 'uhmm-transcript-item';

    // Speaker and text
    const textEl = document.createElement('div');
    textEl.className = 'uhmm-text';
    textEl.textContent = `${item.speaker}: "${item.text}"`;
    itemEl.appendChild(textEl);

    // Verdict alert (if exists and not supported)
    if (item.verdict) {
      const verdictEl = document.createElement('div');
      verdictEl.className = `uhmm-verdict uhmm-verdict-${item.verdict.status}`;

      const statusIcons = {
        contradicted: '❌',
        unclear: '⚠️',
        not_found: '⚪'
      };

      const statusLabels = {
        contradicted: 'FALSE',
        unclear: 'UNCLEAR',
        not_found: 'NO DATA'
      };

      verdictEl.innerHTML = `
        <div class="uhmm-verdict-header">
          <span class="uhmm-verdict-icon">${statusIcons[item.verdict.status]}</span>
          <span class="uhmm-verdict-label">${statusLabels[item.verdict.status]}</span>
          ${item.verdict.confidence ? `<span class="uhmm-verdict-confidence">${Math.round(item.verdict.confidence * 100)}%</span>` : ''}
        </div>
        <div class="uhmm-verdict-rationale">${item.verdict.rationale}</div>
        ${item.verdict.evidenceUrl ? `<a href="${item.verdict.evidenceUrl}" target="_blank" class="uhmm-verdict-link">🔗 View Source</a>` : ''}
      `;

      itemEl.appendChild(verdictEl);
    }

    transcriptList.appendChild(itemEl);
  });

  // Auto-scroll to bottom
  transcriptList.scrollTop = transcriptList.scrollHeight;
}

// Update connection status indicator
function updateConnectionStatus(connected) {
  const statusIndicator = document.getElementById('connection-status');
  const statusText = document.getElementById('status-text');

  if (!statusIndicator || !statusText) return;

  if (connected) {
    statusIndicator.className = 'uhmm-status-indicator connected';
    statusText.textContent = 'Connected';
  } else {
    statusIndicator.className = 'uhmm-status-indicator disconnected';
    statusText.textContent = 'Waiting...';
  }
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[UhmmActually] Received message:', message);

  if (message.type === 'transcript') {
    createOverlay();
    updateConnectionStatus(true);
    addTranscript(message.data);
  } else if (message.type === 'verdict') {
    createOverlay();
    addVerdict(message.data);
  } else if (message.type === 'connection') {
    console.log('[UhmmActually] Connection status:', message.action);
    if (overlayContainer) {
      updateConnectionStatus(message.action === 'connected');
    }
  }

  sendResponse({ received: true });
  return true;
});

// Initialize - Show overlay immediately to indicate meeting detected
window.addEventListener('load', () => {
  // Wait a bit for page to fully load
  setTimeout(() => {
    createOverlay();
    console.log('[UhmmActually] Meeting detected! Overlay ready.');
  }, 2000);
});

console.log('[UhmmActually] Ready to receive messages');
