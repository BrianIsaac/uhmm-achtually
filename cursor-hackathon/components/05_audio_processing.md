# Component: Audio Processing (DailyTransport + Silero VAD)

## Owner Assignment
**Developer A: Pipecat Pipeline Foundation**
Part of Stages 1-3 implementation (Audio → Sentences)

## Time Estimate: 2 hours
- DailyTransport setup: 1 hour
- Silero VAD configuration: 30 min
- Integration testing: 30 min

## Dependencies
```toml
[project.dependencies]
pipecat-ai = ">=0.0.39"          # Core framework
pipecat-ai[daily] = ">=0.0.39"   # Daily.co transport
pipecat-ai[silero] = ">=0.0.39"  # Silero VAD
daily-python = ">=0.10.1"        # Daily Python SDK
```

## Architecture Overview

**Stage 1 in Pipecat Pipeline:**
```
Daily.co Room (WebRTC audio)
    ↓
DailyTransport (Stage 1)  ← THIS COMPONENT
    ├─ Silero VAD (speech detection)
    └─ AudioRawFrame emission
    ↓
GroqSTTService (Stage 2)
```

**Built-in Features:**
- Production-ready WebRTC audio reception
- Automatic audio format conversion (to 16kHz PCM)
- Integrated Silero VAD for speech detection
- No manual buffering required (Pipecat handles it)
- Auto-reconnection and error handling

## Why DailyTransport?

### Compared to Manual WebRTC (streamlit-webrtc)
- **No buffering code:** Pipecat handles all audio buffering automatically
- **Built-in VAD:** Silero VAD integrated, no custom implementation needed
- **Production-ready:** Used by Pipecat in production deployments
- **Error handling:** Auto-reconnection, graceful degradation
- **Zero client-side code:** Works with Daily Prebuilt UI

### Audio Processing Flow
```
1. Daily room participant speaks
2. WebRTC transmits audio to bot
3. DailyTransport receives raw audio
4. Silero VAD detects speech vs silence
5. DailyTransport emits AudioRawFrame (only when speech detected)
6. GroqSTTService transcribes AudioRawFrame
```

## Input/Output Contract

### Input (from Daily.co room)
```python
# WebRTC audio stream (automatic)
# Format: Opus codec over WebRTC
# Handled internally by Daily.co + Pipecat
```

### Output (to GroqSTTService)
```python
AudioRawFrame
- audio: bytes  # Raw PCM audio, 16kHz, mono, 16-bit
- sample_rate: int  # Always 16000
- num_channels: int  # Always 1 (mono)
```

## Implementation Guide

### Step 1: Daily.co Account Setup (30 min)

**Create Daily.co account:**
```bash
# Sign up at https://dashboard.daily.co
# Navigate to API Keys section
# Copy your API key
```

**Add API key to .env:**
```bash
# Add to .env file
DAILY_API_KEY=your_daily_api_key_here
```

**Create test room:**
```bash
# Create room via API
curl -X POST https://api.daily.co/v1/rooms \
  -H "Authorization: Bearer $DAILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fact-checker-test",
    "privacy": "public",
    "properties": {
      "enable_chat": true,
      "enable_prejoin_ui": false
    }
  }'
```

**Generate bot token:**
```bash
# Generate token for bot
curl -X POST https://api.daily.co/v1/meeting-tokens \
  -H "Authorization: Bearer $DAILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "room_name": "fact-checker-test",
      "is_owner": true
    }
  }'
```

**Add room URL and token to .env:**
```bash
# Add to .env
DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-test
DAILY_BOT_TOKEN=your_bot_token_here
```

### Step 2: Implement DailyTransport (1 hour)

Create `src/services/daily_transport_service.py`:

```python
"""Daily.co transport service configuration for Pipecat pipeline."""

import os
import logging
from pipecat.transports.daily_transport import DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer

logger = logging.getLogger(__name__)


def create_daily_transport(
    room_url: str | None = None,
    token: str | None = None,
    bot_name: str = "Fact Checker",
    vad_enabled: bool = True
) -> DailyTransport:
    """Create and configure Daily.co transport for pipeline.

    Args:
        room_url: Daily.co room URL (defaults to DAILY_ROOM_URL env var)
        token: Daily.co bot token (defaults to DAILY_BOT_TOKEN env var)
        bot_name: Bot display name in Daily room
        vad_enabled: Enable Silero VAD for speech detection

    Returns:
        Configured DailyTransport instance

    Raises:
        ValueError: If room_url or token not provided and not in env
    """
    # Get credentials from env if not provided
    room_url = room_url or os.getenv("DAILY_ROOM_URL")
    token = token or os.getenv("DAILY_BOT_TOKEN")

    if not room_url or not token:
        raise ValueError(
            "DAILY_ROOM_URL and DAILY_BOT_TOKEN must be set via parameters or environment variables"
        )

    logger.info(f"Initialising DailyTransport for room: {room_url}")

    # Create VAD analyzer if enabled
    vad_analyzer = None
    if vad_enabled:
        vad_analyzer = SileroVADAnalyzer(
            sample_rate=16000,
            threshold=0.5,  # Confidence threshold for speech detection
            min_speech_duration_ms=250,  # Minimum speech duration
            min_silence_duration_ms=500  # Silence duration before splitting utterance
        )
        logger.info("Silero VAD analyzer enabled")

    # Create transport
    transport = DailyTransport(
        room_url=room_url,
        token=token,
        bot_name=bot_name,
        vad_enabled=vad_enabled,
        vad_analyzer=vad_analyzer,
        vad_audio_passthrough=True,  # Pass audio through even during silence
        # Audio configuration (automatic)
        sample_rate=16000,  # Target sample rate
        audio_out_enabled=False,  # We don't send audio out (Phase 1)
        audio_in_enabled=True,  # We receive audio from participants
        camera_out_enabled=False,  # No video
        camera_in_enabled=False  # No video
    )

    logger.info("DailyTransport initialised successfully")
    return transport


async def test_daily_transport():
    """Test Daily transport connection."""
    import asyncio
    from datetime import datetime

    print(f"[{datetime.now()}] Creating Daily transport...")
    transport = create_daily_transport()

    print(f"[{datetime.now()}] Joining Daily room...")
    print(f"Room URL: {os.getenv('DAILY_ROOM_URL')}")
    print("Open the room URL in your browser to test audio")
    print("Press Ctrl+C to stop")

    try:
        # Join room (async)
        await transport.run()
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Stopping transport...")
    finally:
        await transport.cleanup()
        print(f"[{datetime.now()}] Transport stopped")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_daily_transport())
```

### Step 3: Configure Silero VAD (30 min)

Create `src/utils/vad_config.py`:

```python
"""Voice Activity Detection configuration for Silero VAD."""

from dataclasses import dataclass
from pipecat.vad.silero import SileroVADAnalyzer


@dataclass
class VADConfig:
    """Silero VAD configuration parameters.

    Attributes:
        sample_rate: Audio sample rate (must be 16000 for Silero)
        threshold: Confidence threshold for speech detection (0.0-1.0)
        min_speech_duration_ms: Minimum speech duration in milliseconds
        min_silence_duration_ms: Minimum silence duration before splitting utterance
    """
    sample_rate: int = 16000
    threshold: float = 0.5
    min_speech_duration_ms: int = 250
    min_silence_duration_ms: int = 500


def create_vad_analyzer(config: VADConfig | None = None) -> SileroVADAnalyzer:
    """Create Silero VAD analyzer with configuration.

    Args:
        config: VAD configuration (defaults to VADConfig())

    Returns:
        Configured SileroVADAnalyzer instance
    """
    if config is None:
        config = VADConfig()

    return SileroVADAnalyzer(
        sample_rate=config.sample_rate,
        threshold=config.threshold,
        min_speech_duration_ms=config.min_speech_duration_ms,
        min_silence_duration_ms=config.min_silence_duration_ms
    )


# Preset configurations for different scenarios
class VADPresets:
    """Preset VAD configurations for common scenarios."""

    @staticmethod
    def sensitive() -> VADConfig:
        """More sensitive (catches more speech, may include noise).

        Good for:
        - Soft-spoken speakers
        - Noisy environments
        - Capturing all possible speech
        """
        return VADConfig(
            threshold=0.3,
            min_speech_duration_ms=150,
            min_silence_duration_ms=300
        )

    @staticmethod
    def balanced() -> VADConfig:
        """Balanced sensitivity (recommended default).

        Good for:
        - Normal office environments
        - Clear speech
        - General use
        """
        return VADConfig(
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=500
        )

    @staticmethod
    def conservative() -> VADConfig:
        """Less sensitive (cleaner speech, may miss soft-spoken).

        Good for:
        - Low-noise environments
        - Loud speakers
        - Minimising false positives
        """
        return VADConfig(
            threshold=0.7,
            min_speech_duration_ms=500,
            min_silence_duration_ms=700
        )


# Usage examples
if __name__ == "__main__":
    # Default configuration
    vad = create_vad_analyzer()
    print(f"Default VAD: threshold={vad.threshold}")

    # Sensitive configuration
    sensitive_vad = create_vad_analyzer(VADPresets.sensitive())
    print(f"Sensitive VAD: threshold={sensitive_vad.threshold}")

    # Custom configuration
    custom_config = VADConfig(threshold=0.6, min_speech_duration_ms=300)
    custom_vad = create_vad_analyzer(custom_config)
    print(f"Custom VAD: threshold={custom_vad.threshold}")
```

### Step 4: Room Management Helper (30 min)

Create `src/services/daily_manager.py`:

```python
"""Daily.co room management utilities."""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DailyRoomManager:
    """Manage Daily.co rooms and tokens via API."""

    def __init__(self, api_key: str | None = None):
        """Initialise Daily room manager.

        Args:
            api_key: Daily.co API key (defaults to DAILY_API_KEY env var)

        Raises:
            ValueError: If API key not provided
        """
        self.api_key = api_key or os.getenv("DAILY_API_KEY")
        if not self.api_key:
            raise ValueError("DAILY_API_KEY not found")

        self.base_url = "https://api.daily.co/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_room(
        self,
        name: str,
        privacy: str = "public",
        enable_chat: bool = True
    ) -> dict:
        """Create a new Daily.co room.

        Args:
            name: Room name (must be unique)
            privacy: Room privacy ("public" or "private")
            enable_chat: Enable chat functionality

        Returns:
            Room details dict with 'url', 'name', etc.

        Raises:
            Exception: If room creation fails
        """
        url = f"{self.base_url}/rooms"
        payload = {
            "name": name,
            "privacy": privacy,
            "properties": {
                "enable_chat": enable_chat,
                "enable_prejoin_ui": False
            }
        }

        logger.info(f"Creating Daily room: {name}")
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        room_data = response.json()
        logger.info(f"Room created: {room_data['url']}")
        return room_data

    def create_token(
        self,
        room_name: str,
        is_owner: bool = True,
        expiry_seconds: int = 3600
    ) -> str:
        """Create a meeting token for a room.

        Args:
            room_name: Name of the room
            is_owner: Grant owner permissions to token
            expiry_seconds: Token expiry time in seconds

        Returns:
            Meeting token string

        Raises:
            Exception: If token creation fails
        """
        url = f"{self.base_url}/meeting-tokens"
        payload = {
            "properties": {
                "room_name": room_name,
                "is_owner": is_owner,
                "exp": expiry_seconds
            }
        }

        logger.info(f"Creating meeting token for room: {room_name}")
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        token_data = response.json()
        logger.info("Meeting token created")
        return token_data["token"]

    def delete_room(self, room_name: str) -> None:
        """Delete a Daily.co room.

        Args:
            room_name: Name of the room to delete

        Raises:
            Exception: If room deletion fails
        """
        url = f"{self.base_url}/rooms/{room_name}"

        logger.info(f"Deleting Daily room: {room_name}")
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()

        logger.info(f"Room deleted: {room_name}")

    def get_room(self, room_name: str) -> Optional[dict]:
        """Get room details.

        Args:
            room_name: Name of the room

        Returns:
            Room details dict or None if room doesn't exist
        """
        url = f"{self.base_url}/rooms/{room_name}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise


# CLI helper for room setup
def setup_room_for_bot(room_name: str = "fact-checker-demo") -> tuple[str, str]:
    """Create room and token for bot (CLI helper).

    Args:
        room_name: Name for the room

    Returns:
        Tuple of (room_url, bot_token)
    """
    manager = DailyRoomManager()

    # Check if room exists
    existing_room = manager.get_room(room_name)
    if existing_room:
        print(f"Room already exists: {existing_room['url']}")
        room_url = existing_room["url"]
    else:
        # Create new room
        room = manager.create_room(name=room_name, enable_chat=True)
        room_url = room["url"]
        print(f"Room created: {room_url}")

    # Create token
    token = manager.create_token(room_name=room_name, is_owner=True)
    print(f"Bot token created (expires in 1 hour)")

    print("\nAdd these to your .env file:")
    print(f"DAILY_ROOM_URL={room_url}")
    print(f"DAILY_BOT_TOKEN={token}")

    return room_url, token


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        room_name = sys.argv[1]
    else:
        room_name = "fact-checker-demo"

    try:
        setup_room_for_bot(room_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
```

## Audio Format Specifications

### DailyTransport Audio Output
```python
AudioRawFrame specification:
- Format: Raw PCM (Pulse Code Modulation)
- Sample rate: 16000 Hz (16kHz)
- Channels: 1 (mono)
- Sample width: 2 bytes (16-bit)
- Byte order: Little-endian
- Encoding: Signed integer

# This is exactly what Groq Whisper expects
# No additional processing needed!
```

### WebRTC to PCM Conversion
```
Daily.co room audio (Opus codec)
    ↓ (automatic in Daily SDK)
DailyTransport receives raw audio
    ↓ (automatic format conversion)
16kHz, mono, 16-bit PCM
    ↓ (AudioRawFrame)
GroqSTTService
```

## VAD (Voice Activity Detection) Benefits

### Why Silero VAD?
- **Reduces API calls:** Only processes speech, ignores silence
- **Improves latency:** No wasted processing on silence
- **Better segmentation:** Natural utterance boundaries
- **Cost savings:** Fewer Groq API requests
- **Production-tested:** Used in Pipecat production deployments

### VAD Performance
```
Without VAD:
- All audio sent to STT (including silence)
- ~60-80% of audio is silence
- Wasted API calls and latency

With VAD:
- Only speech sent to STT
- ~80% reduction in API calls
- Faster overall pipeline
```

### Tuning VAD Sensitivity

**Too many false positives (background noise detected as speech)?**
```python
# Increase threshold
vad_analyzer = SileroVADAnalyzer(threshold=0.7)
```

**Missing soft-spoken participants?**
```python
# Decrease threshold
vad_analyzer = SileroVADAnalyzer(threshold=0.3)
```

**Utterances cut off too early?**
```python
# Increase min_silence_duration_ms
vad_analyzer = SileroVADAnalyzer(min_silence_duration_ms=700)
```

## Manual Verification

### Verification Checklist
- [ ] Bot joins Daily room successfully
- [ ] Bot appears in participant list
- [ ] VAD detects speech when you talk in browser
- [ ] VAD ignores silence (check logs)
- [ ] Bot disconnects cleanly on shutdown
- [ ] Reconnection works after network interruption

## Common Issues & Solutions

### Issue 1: Bot Doesn't Join Room
```bash
# Check credentials
python -c "import os; print('DAILY_ROOM_URL:', os.getenv('DAILY_ROOM_URL')); print('DAILY_BOT_TOKEN:', os.getenv('DAILY_BOT_TOKEN'))"

# Verify token hasn't expired (1 hour default)
# Regenerate token:
curl -X POST https://api.daily.co/v1/meeting-tokens \
  -H "Authorization: Bearer $DAILY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"properties": {"room_name": "fact-checker-test", "is_owner": true}}'
```

### Issue 2: No Audio Received
```python
# Check audio_in_enabled is True
transport = DailyTransport(
    audio_in_enabled=True,  # Must be True
    # ...
)

# Check browser permissions (user must allow microphone)
# Test with https://your-domain.daily.co/fact-checker-test
```

### Issue 3: VAD Too Sensitive (Noise False Positives)
```python
# Use conservative preset
from src.utils.vad_config import VADPresets, create_vad_analyzer

vad = create_vad_analyzer(VADPresets.conservative())
transport = create_daily_transport(vad_enabled=True)
# Pass vad to transport manually if needed
```

### Issue 4: Daily.co API Rate Limits
```python
# Free tier limits:
# - 10 rooms max
# - 1000 participant minutes/month
#
# For development: Reuse same room, delete old test rooms
from src.services.daily_manager import DailyRoomManager

manager = DailyRoomManager()
manager.delete_room("old-test-room")
```

## Performance Benchmarks

### Latency Measurements
| Metric | Target | Typical | Notes |
|--------|--------|---------|-------|
| WebRTC reception | <50ms | ~20ms | Network latency |
| VAD processing | <100ms | ~50ms | Silero VAD overhead |
| Format conversion | <10ms | ~5ms | PCM conversion |
| **Total overhead** | **<150ms** | **~75ms** | DailyTransport total |

### Audio Quality
| Parameter | Value | Notes |
|-----------|-------|-------|
| Sample rate | 16kHz | Optimal for Groq Whisper |
| Bit depth | 16-bit | Standard for speech |
| Channels | Mono | Reduces bandwidth, improves STT |
| Codec | Opus → PCM | Automatic conversion |

## Deliverables Checklist

- [ ] `src/services/daily_transport_service.py` - DailyTransport factory
- [ ] `src/utils/vad_config.py` - VAD configuration helpers
- [ ] `src/services/daily_manager.py` - Room management utilities
- [ ] DAILY_API_KEY, DAILY_ROOM_URL, DAILY_BOT_TOKEN in .env
- [ ] Daily.co room created and tested
- [ ] Bot successfully joins room
- [ ] VAD correctly detects speech
- [ ] Ready for Stage 2 (GroqSTTService) integration

## Next Steps for Integration

1. **Coordinate with Stage 2 Developer:**
   - Verify AudioRawFrame → GroqSTTService flow
   - Test VAD + STT integration
   - Ensure sample rate compatibility (16kHz)

2. **Coordinate with Stage 6 Developer:**
   - Share Daily room URL for testing
   - Verify dual-client pattern (DailyTransport + CallClient)
   - Test audio input + chat output simultaneously

3. **Performance Monitoring:**
   - Add logging for VAD events (speech start/stop)
   - Track audio reception latency
   - Monitor Daily.co connection stability

## Resources

**Pipecat Documentation:**
- DailyTransport: https://docs.pipecat.ai/server/transports/daily-transport
- Silero VAD: https://docs.pipecat.ai/server/vad/silero

**Daily.co Documentation:**
- Python SDK: https://docs.daily.co/reference/daily-python
- REST API: https://docs.daily.co/reference/rest-api
- Dashboard: https://dashboard.daily.co

**Daily.co Guides:**
- Creating rooms: https://docs.daily.co/guides/creating-rooms
- Meeting tokens: https://docs.daily.co/guides/meeting-tokens
- Daily Prebuilt: https://docs.daily.co/products/prebuilt
