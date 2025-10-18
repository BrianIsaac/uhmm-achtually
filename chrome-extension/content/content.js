/**
 * Content Script - Mascot UI
 * Shows a mascot character that displays fact-check alerts via speech bubbles
 */

console.log('[UhmmActually] Mascot UI loaded');

// State management
let mascotContainer = null;
let mascotImage = null;
let speechBubble = null;
let currentTimeout = null;
let isConnected = false;

// Drag state
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let mascotStartX = 0;
let mascotStartY = 0;

// Create mascot UI
function createMascot() {
  if (mascotContainer) return;

  // Create main container
  mascotContainer = document.createElement('div');
  mascotContainer.id = 'uhmm-actually-mascot';
  mascotContainer.className = 'uhmm-mascot-container';

  // Create mascot image
  mascotImage = document.createElement('img');
  mascotImage.className = 'uhmm-mascot-image';
  mascotImage.src = chrome.runtime.getURL('assets/thinking-pose.png');
  mascotImage.alt = 'Fact Check Mascot';

  // Create speech bubble (initially hidden)
  speechBubble = document.createElement('div');
  speechBubble.className = 'uhmm-speech-bubble hidden';
  speechBubble.innerHTML = `
    <div class="uhmm-bubble-content">
      <div class="uhmm-bubble-header">
        <span class="uhmm-bubble-icon"></span>
        <span class="uhmm-bubble-label"></span>
        <span class="uhmm-bubble-confidence"></span>
        <button class="uhmm-bubble-close">×</button>
      </div>
      <div class="uhmm-bubble-text"></div>
      <div class="uhmm-bubble-rationale"></div>
      <a href="#" class="uhmm-bubble-link hidden" target="_blank">🔗 View Source</a>
    </div>
  `;

  // Create connection status indicator
  const statusIndicator = document.createElement('div');
  statusIndicator.className = 'uhmm-status-dot';
  statusIndicator.title = 'Connection status';

  // Assemble the mascot
  mascotContainer.appendChild(speechBubble);
  mascotContainer.appendChild(statusIndicator);
  mascotContainer.appendChild(mascotImage);

  // Add to page
  document.body.appendChild(mascotContainer);

  // Load saved position or use default
  loadMascotPosition();

  // Add drag handlers to mascot
  mascotImage.addEventListener('mousedown', startDrag);
  document.addEventListener('mousemove', drag);
  document.addEventListener('mouseup', endDrag);

  // Add close button handler
  const closeBtn = speechBubble.querySelector('.uhmm-bubble-close');
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    hideSpeechBubble();
  });

  console.log('[UhmmActually] Mascot created');
}

// Show verdict in speech bubble (only for contradicted or unclear)
function showVerdict(data) {
  if (!data.status || data.status === 'supported' || data.status === 'not_found') {
    // Don't show speech bubble for supported facts or no data
    return;
  }

  // Set to talking pose
  setMascotPose('talking');

  // Update speech bubble content
  const bubble = speechBubble;
  const icon = bubble.querySelector('.uhmm-bubble-icon');
  const label = bubble.querySelector('.uhmm-bubble-label');
  const confidence = bubble.querySelector('.uhmm-bubble-confidence');
  const text = bubble.querySelector('.uhmm-bubble-text');
  const rationale = bubble.querySelector('.uhmm-bubble-rationale');
  const link = bubble.querySelector('.uhmm-bubble-link');

  // Set status-specific styling
  speechBubble.className = `uhmm-speech-bubble uhmm-verdict-${data.status}`;

  // Icons and labels for different verdicts
  const statusConfig = {
    contradicted: {
      icon: '❌',
      label: 'FALSE',
      className: 'contradicted'
    },
    unclear: {
      icon: '⚠️',
      label: 'UNCLEAR',
      className: 'unclear'
    }
  };

  const config = statusConfig[data.status];
  if (config) {
    icon.textContent = config.icon;
    label.textContent = config.label;
    bubble.classList.add(`uhmm-verdict-${config.className}`);
  }

  // Set confidence if available
  if (data.confidence !== undefined) {
    confidence.textContent = `${Math.round(data.confidence * 100)}%`;
    confidence.style.display = 'inline-block';
  } else {
    confidence.style.display = 'none';
  }

  // Set claim text
  text.textContent = `"${data.claim || data.transcript}"`;

  // Set rationale
  rationale.textContent = data.rationale || 'Unable to verify this claim.';

  // Set evidence link
  if (data.evidence_url) {
    link.href = data.evidence_url;
    link.classList.remove('hidden');
  } else {
    link.classList.add('hidden');
  }

  // Show the speech bubble
  speechBubble.classList.remove('hidden');

  // Add animation
  speechBubble.style.animation = 'popIn 0.3s ease-out';

  // Auto-hide after 10 seconds (but keep thinking pose)
  if (currentTimeout) {
    clearTimeout(currentTimeout);
  }
  currentTimeout = setTimeout(() => {
    hideSpeechBubble();
  }, 10000);

  // Return to thinking pose after 2 seconds
  setTimeout(() => {
    setMascotPose('thinking');
  }, 2000);
}

// Set mascot pose
function setMascotPose(pose) {
  if (!mascotImage) return;

  if (pose === 'talking') {
    mascotImage.src = chrome.runtime.getURL('assets/talking-pose.png');
    mascotImage.classList.add('talking');
  } else {
    mascotImage.src = chrome.runtime.getURL('assets/thinking-pose.png');
    mascotImage.classList.remove('talking');
  }
}

// Toggle speech bubble visibility
function toggleSpeechBubble() {
  if (speechBubble.classList.contains('hidden')) {
    // If there's content, show it
    if (speechBubble.querySelector('.uhmm-bubble-text').textContent) {
      speechBubble.classList.remove('hidden');
    }
  } else {
    hideSpeechBubble();
  }
}

// Hide speech bubble
function hideSpeechBubble() {
  speechBubble.classList.add('hidden');
  setMascotPose('thinking');
  if (currentTimeout) {
    clearTimeout(currentTimeout);
    currentTimeout = null;
  }
}

// Update connection status
function updateConnectionStatus(connected) {
  isConnected = connected;
  const statusDot = document.querySelector('.uhmm-status-dot');
  if (statusDot) {
    statusDot.className = `uhmm-status-dot ${connected ? 'connected' : 'disconnected'}`;
    statusDot.title = connected ? 'Connected to fact-checker' : 'Waiting for connection...';
  }

  // Animate mascot on connection
  if (connected && mascotImage) {
    mascotImage.style.animation = 'bounce 0.5s ease-out';
    setTimeout(() => {
      mascotImage.style.animation = '';
    }, 500);
  }
}

// Drag functionality
function startDrag(e) {
  if (e.button !== 0) return; // Only left mouse button

  isDragging = true;
  mascotImage.classList.add('dragging');

  // Record starting positions
  dragStartX = e.clientX;
  dragStartY = e.clientY;

  // Get current mascot position
  const rect = mascotContainer.getBoundingClientRect();
  mascotStartX = rect.left;
  mascotStartY = rect.top;

  e.preventDefault();
  e.stopPropagation();
}

function drag(e) {
  if (!isDragging) return;

  // Calculate new position
  const deltaX = e.clientX - dragStartX;
  const deltaY = e.clientY - dragStartY;

  let newX = mascotStartX + deltaX;
  let newY = mascotStartY + deltaY;

  // Keep mascot within viewport bounds
  const maxX = window.innerWidth - mascotContainer.offsetWidth;
  const maxY = window.innerHeight - mascotContainer.offsetHeight;

  newX = Math.max(0, Math.min(newX, maxX));
  newY = Math.max(0, Math.min(newY, maxY));

  // Update position
  mascotContainer.style.left = `${newX}px`;
  mascotContainer.style.top = `${newY}px`;
  mascotContainer.style.right = 'auto';
  mascotContainer.style.bottom = 'auto';

  e.preventDefault();
}

function endDrag(e) {
  if (!isDragging) return;

  isDragging = false;
  mascotImage.classList.remove('dragging');

  // Save position to localStorage
  saveMascotPosition();

  e.preventDefault();
  e.stopPropagation();
}

// Save mascot position to localStorage
function saveMascotPosition() {
  const rect = mascotContainer.getBoundingClientRect();
  const position = {
    left: rect.left,
    top: rect.top
  };
  chrome.storage.local.set({ mascotPosition: position });
}

// Load mascot position from localStorage
function loadMascotPosition() {
  chrome.storage.local.get(['mascotPosition'], (result) => {
    if (result.mascotPosition) {
      const pos = result.mascotPosition;

      // Ensure position is within current viewport
      const maxX = window.innerWidth - mascotContainer.offsetWidth;
      const maxY = window.innerHeight - mascotContainer.offsetHeight;

      const x = Math.max(0, Math.min(pos.left, maxX));
      const y = Math.max(0, Math.min(pos.top, maxY));

      mascotContainer.style.left = `${x}px`;
      mascotContainer.style.top = `${y}px`;
      mascotContainer.style.right = 'auto';
      mascotContainer.style.bottom = 'auto';
    }
    // Otherwise use default CSS positioning (bottom-right)
  });
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[UhmmActually] Received message:', message);

  if (message.type === 'verdict') {
    createMascot();
    showVerdict(message.data);
  } else if (message.type === 'connection') {
    createMascot();
    updateConnectionStatus(message.action === 'connected');
  } else if (message.type === 'transcript') {
    // We only care about verdicts now, but ensure mascot exists
    createMascot();
    updateConnectionStatus(true);
  }

  sendResponse({ received: true });
  return true;
});

// Initialize mascot on page load
window.addEventListener('load', () => {
  setTimeout(() => {
    createMascot();
    console.log('[UhmmActually] Mascot ready!');
  }, 2000);
});

console.log('[UhmmActually] Mascot script ready');