# Developer C: Vue.js Frontend + Daily.co Integration (8 hours)

## Your Role
You are Developer C, responsible for building the custom Vue.js frontend that displays fact-check verdicts in real-time. You'll create a branded UI with video participants, verdict cards, and seamless integration with the backend via Daily.co app messages.

**IMPORTANT**:
1. **Daily.co Setup**: You create the Daily.co room and share credentials with Developers A & B
2. **What Daily Provides**: ONLY WebRTC room infrastructure (NOT bot hosting)
3. **Backend Bot**: Runs on Developer A or B's laptop, NOT in Daily's cloud
4. **Your Frontend**: Runs in browser (localhost:5173 for dev)

## Project Context
Building a real-time AI fact-checker bot that joins Daily.co video meetings, listens to conversations, extracts factual claims, verifies them via web search, and displays results in a custom Vue.js frontend. This is a **24-hour hackathon** with a 3-person team.

## Architecture Overview
**Triple-Client Pattern:**
- **Vue.js CallObject (Frontend - YOU)**: Custom UI with audio/video + app message listener
- **Pipecat DailyTransport (Backend - Developer A)**: Audio pipeline processing (Stages 1-3)
- **Daily CallClient (Backend - Developer B)**: Claim processing + app message broadcasting (Stages 4-6)

## Your Deliverables (Hours 0-8)

### H 0-1: Project Setup & Daily.co Infrastructure
**Goal**: Set up Vue.js project and Daily.co account

**Tasks**:
1. **Set up Daily.co account**:
   - Sign up at https://dashboard.daily.co
   - Navigate to "API Keys" section
   - Copy your API key
   - Save it securely

   **What you're getting**: Daily.co provides WebRTC infrastructure (room URL, signaling).
   **What you're NOT getting**: Bot hosting. The Python bot runs on Developer A/B's laptop.

2. **Create Daily room via API**:
   ```bash
   curl -X POST https://api.daily.co/v1/rooms \
     -H "Authorization: Bearer YOUR_DAILY_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "fact-checker-demo",
       "privacy": "public",
       "properties": {
         "enable_chat": false,
         "enable_prejoin_ui": false
       }
     }'
   ```

   **Note**: `enable_chat: false` because we're using custom app messages, not Daily Prebuilt chat.

3. **Initialise Vue.js project**:
   ```bash
   cd /home/brian-isaac/Documents/personal/uhmm-achtually
   npm create vite@latest frontend -- --template vue
   cd frontend
   npm install
   ```

4. **Install dependencies**:
   ```bash
   npm install @daily-co/daily-js
   ```

5. **Create .env.local**:
   ```bash
   # frontend/.env.local
   VITE_DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-demo
   ```

6. **Share credentials with Developer A & B**:
   Create a shared document (Google Doc/Notion) with:
   ```
   DAILY_API_KEY=your_api_key_here
   DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-demo
   DAILY_BOT_TOKEN=your_bot_token_here
   ```

   **They need this to**:
   - Run the bot on their laptop
   - Connect to your Daily room

**Deliverable**: Vue.js project set up, Daily room created, credentials shared

**REMINDER**: Daily.co is ONLY the WebRTC room. The Python bot will run on Developer A or B's laptop!

---

### H 1-3: Daily CallObject Integration
**Goal**: Integrate Daily.co for audio/video + app messages

**Tasks**:
1. **Create useDaily.js composable**:
   Create `frontend/src/composables/useDaily.js`:
   ```javascript
   /**
    * Daily.co CallObject wrapper composable.
    * Handles room joining, participants, and event management.
    */
   import { reactive } from 'vue'
   import DailyIframe from '@daily-co/daily-js'

   export function useDaily() {
     const callState = reactive({
       callObject: null,
       isJoined: false,
       participants: new Map(),
       localParticipant: null,
       error: null
     })

     /**
      * Initialise Daily CallObject.
      */
     function initializeCall() {
       callState.callObject = DailyIframe.createCallObject({
         subscribeToTracksAutomatically: true,
         audioSource: true,
         videoSource: true
       })

       // Event handlers
       callState.callObject
         .on('joined-meeting', handleJoinedMeeting)
         .on('participant-joined', handleParticipantJoined)
         .on('participant-updated', handleParticipantUpdated)
         .on('participant-left', handleParticipantLeft)
         .on('app-message', handleAppMessage)
         .on('error', handleError)
     }

     /**
      * Join Daily room.
      */
     async function joinCall(roomUrl) {
       if (!callState.callObject) {
         initializeCall()
       }

       try {
         await callState.callObject.join({ url: roomUrl })
         callState.isJoined = true
       } catch (error) {
         callState.error = error.message
         console.error('Failed to join call:', error)
       }
     }

     /**
      * Leave Daily room.
      */
     async function leaveCall() {
       if (callState.callObject) {
         await callState.callObject.leave()
         callState.isJoined = false
         callState.participants.clear()
       }
     }

     /**
      * Toggle microphone.
      */
     function toggleMicrophone() {
       if (callState.callObject) {
         const isEnabled = callState.callObject.localAudio()
         callState.callObject.setLocalAudio(!isEnabled)
       }
     }

     /**
      * Toggle camera.
      */
     function toggleCamera() {
       if (callState.callObject) {
         const isEnabled = callState.callObject.localVideo()
         callState.callObject.setLocalVideo(!isEnabled)
       }
     }

     // Event Handlers
     function handleJoinedMeeting(event) {
       console.log('Joined meeting:', event)
       callState.localParticipant = event.participants.local

       // Add all participants
       Object.entries(event.participants).forEach(([id, participant]) => {
         callState.participants.set(id, participant)
       })
     }

     function handleParticipantJoined(event) {
       console.log('Participant joined:', event.participant)
       callState.participants.set(event.participant.session_id, event.participant)
     }

     function handleParticipantUpdated(event) {
       const participant = callState.participants.get(event.participant.session_id)
       if (participant) {
         Object.assign(participant, event.participant)
       }
     }

     function handleParticipantLeft(event) {
       console.log('Participant left:', event.participant)
       callState.participants.delete(event.participant.session_id)
     }

     function handleAppMessage(event) {
       // This will be handled by useFactCheck composable
       console.log('App message received:', event.data)
     }

     function handleError(event) {
       console.error('Daily error:', event)
       callState.error = event.errorMsg
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

2. **Create CallControls.vue component**:
   Create `frontend/src/components/CallControls.vue`:
   ```vue
   <template>
     <div class="call-controls">
       <button
         v-if="!isJoined"
         @click="handleJoin"
         class="btn btn-primary"
       >
         Join Call
       </button>

       <div v-else class="controls-group">
         <button @click="toggleMic" :class="['btn', micEnabled ? 'btn-active' : 'btn-muted']">
           {{ micEnabled ? '🎤' : '🔇' }}
         </button>

         <button @click="toggleCam" :class="['btn', camEnabled ? 'btn-active' : 'btn-muted']">
           {{ camEnabled ? '📹' : '📵' }}
         </button>

         <button @click="handleLeave" class="btn btn-danger">
           Leave
         </button>
       </div>
     </div>
   </template>

   <script setup>
   import { ref, computed } from 'vue'

   const props = defineProps({
     callObject: Object,
     isJoined: Boolean
   })

   const emit = defineEmits(['join', 'leave', 'toggle-mic', 'toggle-cam'])

   const micEnabled = ref(true)
   const camEnabled = ref(true)

   function handleJoin() {
     emit('join')
   }

   function handleLeave() {
     emit('leave')
   }

   function toggleMic() {
     micEnabled.value = !micEnabled.value
     emit('toggle-mic')
   }

   function toggleCam() {
     camEnabled.value = !camEnabled.value
     emit('toggle-cam')
   }
   </script>

   <style scoped>
   .call-controls {
     padding: 1rem;
     background: #1a1a1a;
     border-radius: 8px;
     display: flex;
     gap: 1rem;
     justify-content: centre;
   }

   .controls-group {
     display: flex;
     gap: 0.5rem;
   }

   .btn {
     padding: 0.75rem 1.5rem;
     border: none;
     border-radius: 6px;
     font-size: 1rem;
     cursor: pointer;
     transition: all 0.2s;
   }

   .btn-primary {
     background: #4CAF50;
     colour: white;
   }

   .btn-primary:hover {
     background: #45a049;
   }

   .btn-active {
     background: #333;
     colour: white;
   }

   .btn-muted {
     background: #555;
     colour: #999;
   }

   .btn-danger {
     background: #f44336;
     colour: white;
   }

   .btn-danger:hover {
     background: #da190b;
   }
   </style>
   ```

3. **Manual verification**:
   - Join room with browser
   - Verify audio/video working
   - Check participant list updates
   - Test mic/camera toggles

**Deliverable**: Daily CallObject integrated, audio/video working

---

### H 3-5: Fact-Check Display & App Message Handling
**Goal**: Display fact-check verdicts from backend

**Tasks**:
1. **Understand app message format from Developer B**:
   ```javascript
   {
     type: 'fact-check-verdict',
     claim: 'Python 3.12 removed the distutils package',
     status: 'supported',  // 'supported', 'contradicted', 'unclear', 'not_found'
     confidence: 0.95,
     rationale: 'PEP 632 explicitly deprecated distutils',
     evidence_url: 'https://peps.python.org/pep-0632/'
   }
   ```

2. **Create useFactCheck.js composable**:
   Create `frontend/src/composables/useFactCheck.js`:
   ```javascript
   /**
    * Fact-check verdict management composable.
    * Handles app messages from backend and verdict state.
    */
   import { ref } from 'vue'

   export function useFactCheck(callObject) {
     const verdicts = ref([])

     /**
      * Initialise app message listener.
      */
     function initializeAppMessageListener() {
       if (callObject) {
         callObject.on('app-message', handleAppMessage)
       }
     }

     /**
      * Handle incoming app messages from backend.
      */
     function handleAppMessage(event) {
       console.log('App message:', event.data)

       if (event.data.type === 'fact-check-verdict') {
         const verdict = {
           id: Date.now() + Math.random(), // Unique ID
           claim: event.data.claim,
           status: event.data.status,
           confidence: event.data.confidence,
           rationale: event.data.rationale,
           evidenceUrl: event.data.evidence_url,
           timestamp: new Date()
         }

         // Add to beginning of array (newest first)
         verdicts.value.unshift(verdict)

         // Keep only last 20 verdicts
         if (verdicts.value.length > 20) {
           verdicts.value = verdicts.value.slice(0, 20)
         }
       }
     }

     /**
      * Clear all verdicts.
      */
     function clearVerdicts() {
       verdicts.value = []
     }

     return {
       verdicts,
       initializeAppMessageListener,
       clearVerdicts
     }
   }
   ```

3. **Create FactCheckDisplay.vue component**:
   Create `frontend/src/components/FactCheckDisplay.vue`:
   ```vue
   <template>
     <div class="fact-check-display">
       <div class="header">
         <h2>Fact Checks</h2>
         <span class="count">{{ verdicts.length }}</span>
       </div>

       <div class="verdicts-list">
         <div
           v-for="verdict in verdicts"
           :key="verdict.id"
           :class="['verdict-card', `verdict-${verdict.status}`]"
         >
           <div class="verdict-header">
             <span class="status-icon">{{ getStatusIcon(verdict.status) }}</span>
             <span class="status-text">{{ verdict.status.toUpperCase() }}</span>
             <span class="confidence">{{ (verdict.confidence * 100).toFixed(0) }}%</span>
           </div>

           <div class="claim-text">{{ verdict.claim }}</div>

           <div class="rationale">{{ verdict.rationale }}</div>

           <div class="verdict-footer">
             <a
               v-if="verdict.evidenceUrl"
               :href="verdict.evidenceUrl"
               target="_blank"
               class="evidence-link"
             >
               🔗 View Source
             </a>
             <span class="timestamp">{{ formatTime(verdict.timestamp) }}</span>
           </div>
         </div>

         <div v-if="verdicts.length === 0" class="empty-state">
           <p>No fact-checks yet. Start speaking to see verdicts!</p>
         </div>
       </div>
     </div>
   </template>

   <script setup>
   defineProps({
     verdicts: Array
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
   .fact-check-display {
     flex: 1;
     display: flex;
     flex-direction: column;
     background: #1a1a1a;
     border-radius: 8px;
     padding: 1rem;
     overflow: hidden;
   }

   .header {
     display: flex;
     justify-content: space-between;
     align-items: centre;
     margin-bottom: 1rem;
     padding-bottom: 1rem;
     border-bottom: 2px solid #333;
   }

   .header h2 {
     margin: 0;
     colour: white;
     font-size: 1.5rem;
   }

   .count {
     background: #333;
     colour: white;
     padding: 0.25rem 0.75rem;
     border-radius: 12px;
     font-size: 0.875rem;
   }

   .verdicts-list {
     flex: 1;
     overflow-y: auto;
     display: flex;
     flex-direction: column;
     gap: 1rem;
   }

   .verdict-card {
     background: #2a2a2a;
     border-left: 4px solid;
     border-radius: 6px;
     padding: 1rem;
     animation: slideIn 0.3s ease-out;
   }

   @keyframes slideIn {
     from {
       opacity: 0;
       transform: translateY(-10px);
     }
     to {
       opacity: 1;
       transform: translateY(0);
     }
   }

   .verdict-supported {
     border-left-colour: #4CAF50;
   }

   .verdict-contradicted {
     border-left-colour: #f44336;
   }

   .verdict-unclear {
     border-left-colour: #FFC107;
   }

   .verdict-not_found {
     border-left-colour: #9E9E9E;
   }

   .verdict-header {
     display: flex;
     align-items: centre;
     gap: 0.5rem;
     margin-bottom: 0.75rem;
   }

   .status-icon {
     font-size: 1.25rem;
     font-weight: bold;
   }

   .verdict-supported .status-icon {
     colour: #4CAF50;
   }

   .verdict-contradicted .status-icon {
     colour: #f44336;
   }

   .verdict-unclear .status-icon {
     colour: #FFC107;
   }

   .verdict-not_found .status-icon {
     colour: #9E9E9E;
   }

   .status-text {
     colour: white;
     font-weight: 600;
     font-size: 0.875rem;
   }

   .confidence {
     margin-left: auto;
     background: #333;
     colour: white;
     padding: 0.25rem 0.5rem;
     border-radius: 4px;
     font-size: 0.75rem;
   }

   .claim-text {
     colour: white;
     font-size: 1rem;
     margin-bottom: 0.75rem;
     font-weight: 500;
   }

   .rationale {
     colour: #aaa;
     font-size: 0.875rem;
     margin-bottom: 0.75rem;
     line-height: 1.5;
   }

   .verdict-footer {
     display: flex;
     justify-content: space-between;
     align-items: centre;
   }

   .evidence-link {
     colour: #2196F3;
     text-decoration: none;
     font-size: 0.875rem;
   }

   .evidence-link:hover {
     text-decoration: underline;
   }

   .timestamp {
     colour: #666;
     font-size: 0.75rem;
   }

   .empty-state {
     flex: 1;
     display: flex;
     align-items: centre;
     justify-content: centre;
     colour: #666;
     text-align: centre;
   }
   </style>
   ```

4. **Manual verification**:
   - Test with mock app messages
   - Verify verdict cards render correctly
   - Check colours match status (green/red/yellow/grey)
   - Verify timestamps and confidence display

**Deliverable**: Fact-check verdicts displaying in custom UI

---

### H 5-6: Participant Display & Polish
**Goal**: Display video participants and polish UI

**Tasks**:
1. **Create ParticipantTile.vue component**:
   Create `frontend/src/components/ParticipantTile.vue`:
   ```vue
   <template>
     <div class="participant-tile">
       <video
         ref="videoRef"
         autoplay
         playsinline
         :class="['video-element', { 'audio-only': !participant.video }]"
       />
       <div class="participant-info">
         <span class="participant-name">{{ participant.user_name || 'Guest' }}</span>
         <span v-if="!participant.audio" class="muted-indicator">🔇</span>
       </div>
     </div>
   </template>

   <script setup>
   import { ref, watch, onMounted } from 'vue'

   const props = defineProps({
     participant: Object,
     callObject: Object
   })

   const videoRef = ref(null)

   onMounted(() => {
     updateVideoTrack()
   })

   watch(() => props.participant, () => {
     updateVideoTrack()
   }, { deep: true })

   function updateVideoTrack() {
     if (!videoRef.value || !props.callObject) return

     const sessionId = props.participant.session_id
     const tracks = props.callObject.participants()[sessionId]?.tracks

     if (tracks?.video?.persistentTrack) {
       videoRef.value.srcObject = new MediaStream([tracks.video.persistentTrack])
     } else if (tracks?.audio?.persistentTrack) {
       videoRef.value.srcObject = new MediaStream([tracks.audio.persistentTrack])
     }
   }
   </script>

   <style scoped>
   .participant-tile {
     position: relative;
     background: #000;
     border-radius: 8px;
     overflow: hidden;
     aspect-ratio: 16 / 9;
   }

   .video-element {
     width: 100%;
     height: 100%;
     object-fit: cover;
   }

   .video-element.audio-only {
     background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
   }

   .participant-info {
     position: absolute;
     bottom: 0;
     left: 0;
     right: 0;
     background: linear-gradient(transparent, rgba(0,0,0,0.8));
     padding: 0.5rem;
     display: flex;
     justify-content: space-between;
     align-items: centre;
   }

   .participant-name {
     colour: white;
     font-size: 0.875rem;
     font-weight: 500;
   }

   .muted-indicator {
     font-size: 1rem;
   }
   </style>
   ```

2. **Create main App.vue**:
   Create `frontend/src/App.vue`:
   ```vue
   <template>
     <div class="app">
       <header class="app-header">
         <h1>🔍 Real-Time Fact Checker</h1>
       </header>

       <main class="app-main">
         <div class="video-section">
           <div class="participants-grid">
             <ParticipantTile
               v-for="[id, participant] in callState.participants"
               :key="id"
               :participant="participant"
               :callObject="callState.callObject"
             />
           </div>

           <CallControls
             :callObject="callState.callObject"
             :isJoined="callState.isJoined"
             @join="handleJoin"
             @leave="handleLeave"
             @toggle-mic="toggleMicrophone"
             @toggle-cam="toggleCamera"
           />
         </div>

         <div class="fact-check-section">
           <FactCheckDisplay :verdicts="verdicts" />
         </div>
       </main>
     </div>
   </template>

   <script setup>
   import { onMounted } from 'vue'
   import { useDaily } from './composables/useDaily'
   import { useFactCheck } from './composables/useFactCheck'
   import CallControls from './components/CallControls.vue'
   import FactCheckDisplay from './components/FactCheckDisplay.vue'
   import ParticipantTile from './components/ParticipantTile.vue'

   const roomUrl = import.meta.env.VITE_DAILY_ROOM_URL

   const {
     callState,
     initializeCall,
     joinCall,
     leaveCall,
     toggleMicrophone,
     toggleCamera
   } = useDaily()

   const { verdicts, initializeAppMessageListener } = useFactCheck(null)

   onMounted(() => {
     initializeCall()
   })

   async function handleJoin() {
     await joinCall(roomUrl)
     // Initialise app message listener after joining
     initializeAppMessageListener(callState.callObject)
   }

   async function handleLeave() {
     await leaveCall()
   }
   </script>

   <style>
   * {
     margin: 0;
     padding: 0;
     box-sizing: border-box;
   }

   body {
     font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
     background: #0a0a0a;
     colour: white;
   }

   .app {
     min-height: 100vh;
     display: flex;
     flex-direction: column;
   }

   .app-header {
     background: #1a1a1a;
     padding: 1rem 2rem;
     border-bottom: 2px solid #333;
   }

   .app-header h1 {
     font-size: 1.5rem;
   }

   .app-main {
     flex: 1;
     display: grid;
     grid-template-columns: 1fr 400px;
     gap: 1rem;
     padding: 1rem;
   }

   .video-section {
     display: flex;
     flex-direction: column;
     gap: 1rem;
   }

   .participants-grid {
     flex: 1;
     display: grid;
     grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
     gap: 1rem;
     max-height: calc(100vh - 200px);
     overflow-y: auto;
   }

   .fact-check-section {
     display: flex;
     flex-direction: column;
   }

   @media (max-width: 1024px) {
     .app-main {
       grid-template-columns: 1fr;
     }

     .fact-check-section {
       max-height: 400px;
     }
   }
   </style>
   ```

3. **Polish and responsive design**:
   - Test on different screen sizes
   - Add animations for verdict cards
   - Ensure dark theme throughout
   - Add error states

**Deliverable**: Complete UI with participants and verdicts

---

### H 6-8: Integration Testing & Demo Preparation
**Goal**: Test end-to-end with backend and prepare demo

**Tasks**:
1. **Coordinate with Developer A & B**:
   - Get backend bot running
   - Share Daily room URL
   - Verify they're using correct room

2. **End-to-end testing**:
   - Start frontend: `npm run dev`
   - Start backend bot
   - Join room in browser
   - Speak test claims:
     - "Python 3.12 removed the distutils package."
     - "GDPR requires breach notification within 72 hours."
     - "PostgreSQL 15 uses LLVM JIT compilation by default."
   - Verify verdict cards appear
   - Check colours are correct
   - Verify evidence links work

3. **Test edge cases**:
   - Multiple verdicts appearing quickly
   - Very long claims (text wrapping)
   - Missing evidence URLs
   - All status types (supported/contradicted/unclear/not_found)

4. **Performance verification**:
   - Measure latency from speech to verdict card render
   - Target: <100ms from app-message to display
   - Check for memory leaks (leave running 10+ mins)
   - Verify verdict list doesn't grow infinitely

5. **Create demo script**:
   Save to `frontend/demo_script.md`:
   ```markdown
   # Demo Script

   ## Setup (Before Demo)
   1. Start backend bot: `cd backend && uv run python bot.py`
   2. Start frontend: `cd frontend && npm run dev`
   3. Open http://localhost:5173 in browser

   ## Demo Flow (5 minutes)
   1. Join call (show participants appearing)
   2. Speak: "Python 3.12 removed the distutils package"
      - Wait for green "SUPPORTED" card
      - Click evidence link to show source
   3. Speak: "GDPR requires breach notification within 72 hours"
      - Wait for green "SUPPORTED" card
   4. Speak: "PostgreSQL 15 uses LLVM JIT compilation by default"
      - Wait for red "CONTRADICTED" card
   5. Show verdict history scrolling
   6. Leave call

   ## Talking Points
   - Custom branded UI (not Daily Prebuilt)
   - Real-time fact-checking (<2.5s latency)
   - Evidence-backed verdicts with source links
   - Colour-coded status indicators
   - Clean, professional interface
   ```

6. **Record backup demo video**:
   - Screen recording of successful demo run
   - In case live demo fails
   - Show all features working

**Deliverable**: End-to-end tested, demo-ready frontend

---

## Integration with Other Developers

### You provide to Developer A & B:
- **Daily room URL**: `https://your-domain.daily.co/fact-checker-demo`
- **App message reception confirmation**: Verify you can receive messages
- **UI feedback**: Report any app message format issues

### You receive from Developer B:
- **App message format**:
  ```json
  {
    "type": "fact-check-verdict",
    "claim": "...",
    "status": "supported|contradicted|unclear|not_found",
    "confidence": 0.95,
    "rationale": "...",
    "evidence_url": "..."
  }
  ```

### Testing coordination:
- Join same Daily room as backend bot
- Verify three connections work (your CallObject + their DailyTransport + their CallClient)
- Test verdict cards render correctly
- Report any issues immediately

---

## Success Criteria

By Hour 6, you should have:
- ✅ Vue.js project set up with Vite
- ✅ Daily.co account and room created
- ✅ CallObject integrated with audio/video
- ✅ App message listener working
- ✅ Verdict cards rendering with correct colours
- ✅ Participant tiles displaying video

By Hour 8, you should have:
- ✅ End-to-end tested with backend
- ✅ All test claims displaying correctly
- ✅ UI polished and responsive
- ✅ Demo script prepared
- ✅ Backup demo video recorded

---

## Key Commands

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Important Notes

1. **Hackathon Mode**: Focus on working features, not perfect code
2. **Manual Verification**: Test by joining room and speaking
3. **Triple Connection**: Your CallObject + backend DailyTransport + backend CallClient
4. **App Messages**: Listen for 'app-message' event, not chat messages
5. **Colours**: Green (supported), Red (contradicted), Yellow (unclear), Grey (not_found)
6. **Latency**: Aim for <100ms from app-message to render
7. **Daily.co Free Tier**: Sufficient for hackathon demo

---

## Troubleshooting

**CallObject not joining room**:
- Check VITE_DAILY_ROOM_URL is correct
- Verify room exists (check Daily dashboard)
- Check browser console for errors

**No app messages received**:
- Verify 'app-message' event listener attached
- Check backend is sending to correct room
- Test with simple message first

**Video not displaying**:
- Check camera permissions in browser
- Verify `subscribeToTracksAutomatically: true`
- Check participant.tracks exists

**Verdict cards not rendering**:
- Check app message format matches expected
- Verify `event.data.type === 'fact-check-verdict'`
- Log incoming messages to debug

**Performance issues**:
- Limit verdicts array to 20 items
- Use CSS `will-change` for animations
- Debounce rapid verdict updates

---

## Documentation References

- Daily.co JS SDK: https://docs.daily.co/reference/daily-js
- Vue.js 3: https://vuejs.org/guide/
- Vite: https://vitejs.dev/guide/
- App Messages Example: https://www.daily.co/blog/build-a-custom-chat-widget-with-vue-with-dailys-sendappmessage-method/
- Architecture: See `/cursor-hackathon/architecture_design.md`
- Frontend Spec: See `/cursor-hackathon/components/10_vue_frontend.md`

---

**Good luck, Developer C! You're building the face of the product that users will see. Make it shine! ✨**
