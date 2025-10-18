# Component 10: Vue.js Frontend

**Stage**: Frontend UI + App Message Handler
**Owner**: Developer C (3-4 hours)
**Stack**: Vue.js 3 + Vite + @daily-co/daily-js ^0.73.0
**Purpose**: Custom branded UI for video calls with integrated fact-check display

## Overview

The Vue.js frontend provides a custom, fully-branded user interface for the Real-Time Meeting Fact-Checker. It handles audio/video calling via Daily's Call Object mode and displays fact-check verdicts received as app messages from the Python backend bot.

### Key Responsibilities

1. **Call Management**: Join/leave Daily rooms using `@daily-co/daily-js`
2. **Media Controls**: Microphone and camera toggle
3. **Participant Display**: Show video tiles for all participants
4. **Verdict Display**: Render fact-check results as styled cards
5. **App Message Handling**: Listen for and process app messages from the bot

### Integration Point

- **Receives From**: Python bot via Daily `sendAppMessage()` → triggers `'app-message'` event
- **Sends To**: Daily.co (audio/video streams)
- **Does NOT**: Process audio or perform fact-checking (that's all backend)

---

## Technology Stack

### Dependencies (package.json)

```json
{
  "name": "fact-checker-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@daily-co/daily-js": "^0.73.0",
    "vue": "^3.2.40"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.4",
    "vite": "^5.4.10"
  }
}
```

### Why This Stack?

| Technology | Reason |
|------------|--------|
| **Vue.js 3** | Simplest reactive framework, less boilerplate than React |
| **Vite** | Lightning-fast dev server (<1s startup), instant HMR |
| **@daily-co/daily-js** | Official Daily Call Object SDK, full WebRTC control |
| **Composition API** | Clean state management without Vuex/Pinia overhead |

---

## Project Structure

```
frontend/
├── src/
│   ├── App.vue                      # Main app component
│   ├── main.js                      # Entry point
│   ├── components/
│   │   ├── CallControls.vue         # Mic/camera toggle buttons
│   │   ├── FactCheckDisplay.vue     # Verdict card list
│   │   └── ParticipantTile.vue      # Video tile for each participant
│   └── composables/
│       ├── useDaily.js              # Daily CallObject wrapper
│       └── useFactCheck.js          # App message handler
├── public/
│   └── index.html
├── .env.local                       # VITE_DAILY_ROOM_URL
├── package.json
└── vite.config.js
```

---

## Core Implementation

### 1. Entry Point (main.js)

```javascript
/**
 * Application entry point
 *
 * Initialises Vue app and mounts to DOM.
 */
import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

createApp(App).mount('#app')
```

### 2. Main App Component (App.vue)

```vue
<template>
  <div class="app">
    <!-- Header -->
    <header class="app-header">
      <h1>Real-Time Meeting Fact-Checker</h1>
      <CallControls
        :is-joined="callState.isJoined"
        :is-microphone-enabled="callState.isMicrophoneEnabled"
        :is-camera-enabled="callState.isCameraEnabled"
        @join="handleJoin"
        @leave="handleLeave"
        @toggle-microphone="toggleMicrophone"
        @toggle-camera="toggleCamera"
      />
    </header>

    <!-- Main Content -->
    <main class="app-main">
      <!-- Participant Video Tiles -->
      <section class="participants-grid">
        <ParticipantTile
          v-for="participant in callState.participants"
          :key="participant.session_id"
          :participant="participant"
        />
      </section>

      <!-- Fact-Check Verdict Display -->
      <aside class="fact-check-panel">
        <FactCheckDisplay :verdicts="verdicts" />
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import CallControls from './components/CallControls.vue'
import FactCheckDisplay from './components/FactCheckDisplay.vue'
import ParticipantTile from './components/ParticipantTile.vue'
import { useDaily } from './composables/useDaily'
import { useFactCheck } from './composables/useFactCheck'

// Daily call management
const {
  callState,
  initializeCall,
  joinCall,
  leaveCall,
  toggleMicrophone,
  toggleCamera
} = useDaily()

// Fact-check verdict handling
const { verdicts, handleAppMessage } = useFactCheck()

// Lifecycle
onMounted(async () => {
  await initializeCall()

  // Listen for app messages from bot
  callState.callObject.on('app-message', handleAppMessage)
})

onUnmounted(() => {
  if (callState.callObject) {
    callState.callObject.off('app-message', handleAppMessage)
    leaveCall()
  }
})

// Event handlers
const handleJoin = () => {
  const roomUrl = import.meta.env.VITE_DAILY_ROOM_URL
  joinCall(roomUrl)
}

const handleLeave = () => {
  leaveCall()
}
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1a1a1a;
  color: #ffffff;
}

.app-header {
  padding: 1rem 2rem;
  background: #2a2a2a;
  border-bottom: 1px solid #404040;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-main {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 1rem;
  padding: 1rem;
  overflow: hidden;
}

.participants-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1rem;
  align-content: start;
  overflow-y: auto;
}

.fact-check-panel {
  background: #2a2a2a;
  border-radius: 8px;
  padding: 1rem;
  overflow-y: auto;
}
</style>
```

### 3. Daily CallObject Composable (useDaily.js)

```javascript
/**
 * Daily CallObject management composable
 *
 * Handles call lifecycle, participant tracking, and media controls.
 */
import { reactive } from 'vue'
import DailyIframe from '@daily-co/daily-js'

export function useDaily() {
  const callState = reactive({
    callObject: null,
    isJoined: false,
    isMicrophoneEnabled: true,
    isCameraEnabled: false,
    participants: []
  })

  /**
   * Initialise Daily CallObject
   */
  async function initializeCall() {
    if (callState.callObject) return

    try {
      callState.callObject = DailyIframe.createCallObject({
        subscribeToTracksAutomatically: true,
        audioSource: true,
        videoSource: false
      })

      // Attach event listeners
      callState.callObject
        .on('joined-meeting', handleJoinedMeeting)
        .on('left-meeting', handleLeftMeeting)
        .on('participant-joined', handleParticipantJoined)
        .on('participant-left', handleParticipantLeft)
        .on('participant-updated', handleParticipantUpdated)
        .on('error', handleError)

      console.log('[Daily] CallObject initialised')
    } catch (error) {
      console.error('[Daily] Initialisation failed:', error)
    }
  }

  /**
   * Join a Daily room
   *
   * @param {string} roomUrl - Daily room URL
   */
  async function joinCall(roomUrl) {
    if (!callState.callObject || callState.isJoined) return

    try {
      await callState.callObject.join({
        url: roomUrl,
        userName: `User-${Math.floor(Math.random() * 1000)}`
      })

      console.log('[Daily] Joined room:', roomUrl)
    } catch (error) {
      console.error('[Daily] Join failed:', error)
    }
  }

  /**
   * Leave the current Daily room
   */
  async function leaveCall() {
    if (!callState.callObject || !callState.isJoined) return

    try {
      await callState.callObject.leave()
      console.log('[Daily] Left room')
    } catch (error) {
      console.error('[Daily] Leave failed:', error)
    }
  }

  /**
   * Toggle microphone on/off
   */
  function toggleMicrophone() {
    if (!callState.callObject) return

    const newState = !callState.isMicrophoneEnabled
    callState.callObject.setLocalAudio(newState)
    callState.isMicrophoneEnabled = newState
    console.log(`[Daily] Microphone ${newState ? 'enabled' : 'disabled'}`)
  }

  /**
   * Toggle camera on/off
   */
  function toggleCamera() {
    if (!callState.callObject) return

    const newState = !callState.isCameraEnabled
    callState.callObject.setLocalVideo(newState)
    callState.isCameraEnabled = newState
    console.log(`[Daily] Camera ${newState ? 'enabled' : 'disabled'}`)
  }

  // Event Handlers

  function handleJoinedMeeting(event) {
    callState.isJoined = true
    updateParticipants()
    console.log('[Daily] Joined meeting:', event)
  }

  function handleLeftMeeting(event) {
    callState.isJoined = false
    callState.participants = []
    console.log('[Daily] Left meeting:', event)
  }

  function handleParticipantJoined(event) {
    console.log('[Daily] Participant joined:', event.participant)
    updateParticipants()
  }

  function handleParticipantLeft(event) {
    console.log('[Daily] Participant left:', event.participant)
    updateParticipants()
  }

  function handleParticipantUpdated(event) {
    updateParticipants()
  }

  function handleError(event) {
    console.error('[Daily] Error:', event)
  }

  function updateParticipants() {
    if (!callState.callObject) return

    const participants = callState.callObject.participants()
    callState.participants = Object.values(participants)
  }

  return {
    callState,
    initializeCall,
    joinCall,
    leaveCall,
    toggleMicrophone,
    toggleCamera
  }
}
```

### 4. Fact-Check Composable (useFactCheck.js)

```javascript
/**
 * Fact-check verdict handler composable
 *
 * Processes app messages from the Python bot and manages verdict state.
 */
import { ref } from 'vue'

export function useFactCheck() {
  const verdicts = ref([])

  /**
   * Handle app message from Daily bot
   *
   * @param {Object} event - Daily app-message event
   * @param {Object} event.data - Message data from bot
   * @param {string} event.fromId - Sender participant ID
   */
  function handleAppMessage(event) {
    console.log('[FactCheck] Received app message:', event)

    // Verify message is from the bot (not from another participant)
    if (!event.data || event.data.type !== 'fact-check-verdict') {
      return
    }

    // Extract verdict data
    const verdict = {
      id: Date.now(), // Unique ID for Vue v-for key
      claim: event.data.claim,
      status: event.data.status, // 'supported', 'contradicted', 'unclear', 'not_found'
      confidence: event.data.confidence,
      rationale: event.data.rationale,
      evidenceUrl: event.data.evidence_url,
      timestamp: new Date()
    }

    // Add to verdicts list (newest first)
    verdicts.value.unshift(verdict)

    console.log(`[FactCheck] Added verdict for claim: "${verdict.claim}"`)
  }

  /**
   * Clear all verdicts
   */
  function clearVerdicts() {
    verdicts.value = []
  }

  return {
    verdicts,
    handleAppMessage,
    clearVerdicts
  }
}
```

### 5. CallControls Component (CallControls.vue)

```vue
<template>
  <div class="call-controls">
    <button
      v-if="!isJoined"
      @click="$emit('join')"
      class="btn btn-primary"
    >
      Join Call
    </button>

    <template v-else>
      <button
        @click="$emit('toggle-microphone')"
        :class="['btn', isMicrophoneEnabled ? 'btn-success' : 'btn-danger']"
      >
        {{ isMicrophoneEnabled ? '🎤 Mute' : '🔇 Unmute' }}
      </button>

      <button
        @click="$emit('toggle-camera')"
        :class="['btn', isCameraEnabled ? 'btn-success' : 'btn-danger']"
      >
        {{ isCameraEnabled ? '📹 Stop Video' : '📹 Start Video' }}
      </button>

      <button
        @click="$emit('leave')"
        class="btn btn-danger"
      >
        Leave Call
      </button>
    </template>
  </div>
</template>

<script setup>
defineProps({
  isJoined: Boolean,
  isMicrophoneEnabled: Boolean,
  isCameraEnabled: Boolean
})

defineEmits(['join', 'leave', 'toggle-microphone', 'toggle-camera'])
</script>

<style scoped>
.call-controls {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn:hover {
  opacity: 0.8;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-danger {
  background: #dc3545;
  color: white;
}
</style>
```

### 6. FactCheckDisplay Component (FactCheckDisplay.vue)

```vue
<template>
  <div class="fact-check-display">
    <h2>Fact Checks</h2>

    <div v-if="verdicts.length === 0" class="empty-state">
      No fact-checks yet. Start speaking to see results.
    </div>

    <div v-else class="verdicts-list">
      <div
        v-for="verdict in verdicts"
        :key="verdict.id"
        :class="['verdict-card', `verdict-${verdict.status}`]"
      >
        <!-- Status Badge -->
        <div class="verdict-header">
          <span class="status-icon">{{ getStatusIcon(verdict.status) }}</span>
          <span class="status-text">
            {{ verdict.status.toUpperCase() }}
            <span v-if="verdict.confidence" class="confidence">
              ({{ Math.round(verdict.confidence * 100) }}%)
            </span>
          </span>
        </div>

        <!-- Claim Text -->
        <div class="claim-text">
          {{ verdict.claim }}
        </div>

        <!-- Rationale -->
        <div class="rationale">
          {{ verdict.rationale }}
        </div>

        <!-- Evidence Link -->
        <a
          v-if="verdict.evidenceUrl"
          :href="verdict.evidenceUrl"
          target="_blank"
          class="evidence-link"
        >
          🔗 View Source
        </a>

        <!-- Timestamp -->
        <div class="timestamp">
          {{ formatTime(verdict.timestamp) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  verdicts: {
    type: Array,
    required: true
  }
})

function getStatusIcon(status) {
  const icons = {
    supported: '✓',
    contradicted: '✗',
    unclear: '?',
    not_found: '∅'
  }
  return icons[status] || '•'
}

function formatTime(date) {
  return date.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}
</script>

<style scoped>
.fact-check-display h2 {
  margin-top: 0;
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.empty-state {
  color: #888;
  text-align: center;
  padding: 2rem;
  font-style: italic;
}

.verdicts-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.verdict-card {
  background: #333;
  border-left: 4px solid;
  border-radius: 4px;
  padding: 1rem;
  transition: transform 0.2s;
}

.verdict-card:hover {
  transform: translateX(4px);
}

.verdict-supported {
  border-color: #28a745;
}

.verdict-contradicted {
  border-color: #dc3545;
}

.verdict-unclear {
  border-color: #ffc107;
}

.verdict-not_found {
  border-color: #6c757d;
}

.verdict-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.status-icon {
  font-size: 1.5rem;
}

.status-text {
  font-weight: bold;
  font-size: 0.9rem;
}

.confidence {
  font-weight: normal;
  opacity: 0.8;
}

.claim-text {
  font-size: 1rem;
  margin-bottom: 0.75rem;
  font-weight: 500;
}

.rationale {
  font-size: 0.9rem;
  color: #ccc;
  line-height: 1.4;
  margin-bottom: 0.75rem;
}

.evidence-link {
  display: inline-block;
  color: #007bff;
  text-decoration: none;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

.evidence-link:hover {
  text-decoration: underline;
}

.timestamp {
  font-size: 0.75rem;
  color: #888;
  text-align: right;
}
</style>
```

### 7. ParticipantTile Component (ParticipantTile.vue)

```vue
<template>
  <div class="participant-tile">
    <video
      v-if="participant.video"
      :ref="el => videoRef = el"
      autoplay
      playsinline
      class="participant-video"
    />
    <div v-else class="participant-placeholder">
      <div class="participant-initials">
        {{ getInitials(participant.user_name) }}
      </div>
    </div>

    <div class="participant-info">
      <span class="participant-name">
        {{ participant.user_name || 'Guest' }}
      </span>
      <span v-if="!participant.audio" class="muted-indicator">🔇</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps({
  participant: {
    type: Object,
    required: true
  }
})

const videoRef = ref(null)

// Update video track when participant changes
watch(() => props.participant.tracks?.video, (track) => {
  if (track && videoRef.value) {
    videoRef.value.srcObject = new MediaStream([track.track])
  }
}, { immediate: true })

function getInitials(name) {
  if (!name) return '?'
  return name
    .split(' ')
    .map(part => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

onUnmounted(() => {
  if (videoRef.value && videoRef.value.srcObject) {
    videoRef.value.srcObject.getTracks().forEach(track => track.stop())
  }
})
</script>

<style scoped>
.participant-tile {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  aspect-ratio: 16 / 9;
}

.participant-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.participant-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.participant-initials {
  font-size: 3rem;
  font-weight: bold;
  color: white;
}

.participant-info {
  position: absolute;
  bottom: 0.5rem;
  left: 0.5rem;
  background: rgba(0, 0, 0, 0.7);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.participant-name {
  font-size: 0.85rem;
  color: white;
}

.muted-indicator {
  font-size: 0.85rem;
}
</style>
```

---

## Configuration

### Environment Variables (.env.local)

```bash
# Daily room URL (must be created via Daily API first)
VITE_DAILY_ROOM_URL=https://yourcompany.daily.co/fact-checker-room
```

### Vite Configuration (vite.config.js)

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true
  }
})
```

---

## Integration with Backend

### App Message Format (from Python bot)

The backend bot sends verdicts in this JSON structure:

```json
{
  "type": "fact-check-verdict",
  "claim": "Microsoft acquired GitHub in 2018",
  "status": "supported",
  "confidence": 0.95,
  "rationale": "Multiple credible sources confirm Microsoft acquired GitHub for $7.5B on June 4, 2018.",
  "evidence_url": "https://blogs.microsoft.com/blog/2018/06/04/microsoft-to-acquire-github/"
}
```

### Python Bot Sending Code

```python
# In fact_check_messenger.py
message_client.sendAppMessage(
    {
        "type": "fact-check-verdict",
        "claim": verdict.claim,
        "status": verdict.status,
        "confidence": verdict.confidence,
        "rationale": verdict.rationale,
        "evidence_url": verdict.evidence_url
    },
    "*"  # Send to all participants
)
```

---

## Testing

### Unit Testing (Optional - Advanced)

Install Vitest for Vue component testing:

```bash
npm install -D vitest @vue/test-utils jsdom
```

### Manual Testing Checklist

1. **Call Join/Leave**:
   - [ ] Join button appears when not connected
   - [ ] Successfully joins Daily room
   - [ ] Leave button appears when connected
   - [ ] Successfully leaves room

2. **Media Controls**:
   - [ ] Microphone toggle works
   - [ ] Camera toggle works (if enabled)
   - [ ] Audio indicator shows muted state

3. **Verdict Display**:
   - [ ] Receives app messages from bot
   - [ ] Displays verdict cards correctly
   - [ ] Shows correct status icon and colour
   - [ ] Evidence links open in new tab

4. **Multi-Participant**:
   - [ ] Shows all participants in grid
   - [ ] Updates when participants join/leave
   - [ ] Video tiles display correctly

---

## Performance Optimisations

### 1. Lazy Loading Components

```javascript
// For large apps, lazy load components
const FactCheckDisplay = defineAsyncComponent(() =>
  import('./components/FactCheckDisplay.vue')
)
```

### 2. Verdict List Virtualisation (if >100 verdicts)

```bash
npm install vue-virtual-scroller
```

### 3. Production Build

```bash
npm run build

# Output in dist/ folder
# Serve with: npm run preview
```

---

## Troubleshooting

### Issue 1: Daily Room Not Joining

```javascript
// Check room URL format
console.log('Room URL:', import.meta.env.VITE_DAILY_ROOM_URL)

// Verify room exists via Daily API
// https://api.daily.co/v1/rooms/{room-name}
```

### Issue 2: App Messages Not Received

```javascript
// Verify event listener is attached
callObject.on('app-message', (event) => {
  console.log('Raw app-message event:', event)
})

// Check bot is sending messages
// Python bot logs should show: "Sent app message"
```

### Issue 3: Vite Environment Variables Not Loading

```bash
# Ensure prefix is VITE_
VITE_DAILY_ROOM_URL=https://...  # ✓ Works
DAILY_ROOM_URL=https://...       # ✗ Won't be exposed to client
```

---

## Deployment

### Development

```bash
npm run dev
# Runs on http://localhost:5173
```

### Production (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel

# Set environment variables in Vercel dashboard:
# VITE_DAILY_ROOM_URL=https://yourcompany.daily.co/room
```

### Production (Netlify)

```bash
# Build
npm run build

# Deploy dist/ folder
netlify deploy --prod --dir=dist
```

---

## Next Steps for Developer C

### Hour 0-1: Setup

1. Create frontend/ directory
2. Install dependencies (`npm install`)
3. Create .env.local with Daily room URL
4. Test basic Vite app runs

### Hour 1-2: Call Object Integration

1. Implement useDaily.js composable
2. Add join/leave functionality
3. Test audio connection with backend bot

### Hour 2-3: Verdict Display

1. Implement useFactCheck.js composable
2. Create FactCheckDisplay.vue component
3. Test app message reception

### Hour 3-4: Polish & Testing

1. Add CallControls.vue component
2. Add ParticipantTile.vue for video display
3. Style verdict cards
4. End-to-end testing with backend bot

---

## Summary

This component provides a complete custom UI for the Real-Time Meeting Fact-Checker. Key features:

✓ **Call Object Mode**: Full control over Daily UI
✓ **App Message Handling**: Receives verdicts from Python bot
✓ **Reactive State**: Vue 3 Composition API for clean code
✓ **Fast Development**: Vite for instant HMR
✓ **Production Ready**: Build and deploy to Vercel/Netlify

**Integration Point**: `'app-message'` event from Daily → `handleAppMessage()` → `verdicts` array → Vue reactive rendering

**Owner**: Developer C (Frontend Specialist)
**Est. Time**: 3-4 hours
**Output**: Fully functional Vue.js app in `frontend/` directory
