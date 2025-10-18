# Component: Daily App Message Delivery (CallClient)

## Owner Assignment
**Developer B: App Message Broadcasting (Stage 6)**
Hours 4-6 (part of backend implementation)

## Time Estimate: 2 hours
- CallClient integration: 1 hour
- App message formatting: 30 min
- Testing with frontend: 30 min

**Note**: Frontend implementation (Developer C) is documented in [10_vue_frontend.md](10_vue_frontend.md)

## Dependencies
```toml
[project.dependencies]
daily-python = ">=0.10.1"        # Daily Python SDK (CallClient)
pipecat-ai = ">=0.0.39"          # FrameProcessor base class
```

## Architecture Overview

**Stage 6 in Pipecat Pipeline:**
```
WebFactChecker (Stage 5)
    ↓ (VerdictFrame)
FactCheckMessenger (Stage 6)  ← THIS COMPONENT
    ├─ CallClient.send_prebuilt_chat_message()
    └─ Message formatting
    ↓
Daily Prebuilt Chat UI
```

**Dual-Client Pattern:**
```
Bot connects to Daily room TWICE:
1. DailyTransport (Stage 1) → Audio input only
2. CallClient (Stage 6) → Chat output only

Why? Pipecat DailyTransport handles audio pipeline.
       CallClient.send_prebuilt_chat_message() simplest for chat.
```

## Why CallClient.send_prebuilt_chat_message()?

### Compared to Other Approaches
- **Custom data channel:** Requires client-side JS code
- **TTS output:** Interrupts speaker flow (deferred to post-MVP)
- **App messaging:** Requires custom UI
- **CallClient.send_prebuilt_chat_message():** Works with Daily Prebuilt out-of-box ✓

### Benefits
- **Zero client-side code:** Uses Daily's hosted Prebuilt UI
- **Immediate visibility:** Messages appear in chat panel
- **Markdown support:** Format verdicts with bold, links, etc.
- **Delivery confirmation:** Completion callbacks for debugging
- **Production-ready:** Used in Daily's AI toolkit examples

## Input/Output Contract

### Input (from WebFactChecker)
```python
VerdictFrame
- claim: str  # "Python 3.12 removed distutils"
- status: str  # "supported", "contradicted", "unclear", "not_found"
- confidence: float  # 0.85
- rationale: str  # "PEP 632 explicitly deprecated distutils"
- evidence_url: str  # "https://peps.python.org/pep-0632/"
```

### Output (to Daily Prebuilt chat)
```
✓ SUPPORTED
PEP 632 explicitly deprecated distutils
[Source](https://peps.python.org/pep-0632/)
```

## Implementation Guide

### Step 1: Daily.co Account Setup (30 min)

**Create Daily.co account:**
```bash
# 1. Sign up at https://dashboard.daily.co
# 2. Navigate to "API Keys" section
# 3. Copy your API key
```

**Add credentials to .env:**
```bash
# Add to .env file
DAILY_API_KEY=your_daily_api_key_here
DAILY_ROOM_URL=https://your-domain.daily.co/fact-checker-demo
DAILY_BOT_TOKEN=your_bot_token_here
```

**Create room programmatically:**
```python
# See src/services/daily_manager.py for full implementation
from src.services.daily_manager import DailyRoomManager

manager = DailyRoomManager()
room = manager.create_room(
    name="fact-checker-demo",
    privacy="public",
    enable_chat=True
)
print(f"Room URL: {room['url']}")
```

### Step 2: FactCheckMessenger Implementation (1.5 hours)

Create `src/processors/fact_check_messenger.py`:

```python
"""Fact-check messenger using Daily CallClient for Prebuilt chat."""

import logging
from typing import AsyncGenerator
from daily import CallClient, Daily
from pipecat.frames import Frame
from pipecat.processors import FrameProcessor
from src.frames.custom_frames import VerdictFrame

logger = logging.getLogger(__name__)


class FactCheckMessengerPrebuilt(FrameProcessor):
    """Send fact-check verdicts to Daily Prebuilt chat using CallClient.

    Uses CallClient.send_prebuilt_chat_message() for zero client-side code.
    Works immediately with Daily Prebuilt UI.

    This is Stage 6 of the Pipecat pipeline.
    """

    # Status emoji mapping
    STATUS_EMOJI = {
        "supported": "✓",
        "contradicted": "✗",
        "unclear": "?",
        "not_found": "∅"
    }

    def __init__(
        self,
        call_client: CallClient,
        bot_name: str = "Fact Checker",
        include_confidence: bool = False
    ):
        """Initialise fact-check messenger.

        Args:
            call_client: Daily CallClient instance (must be joined to room)
            bot_name: Bot display name in chat
            include_confidence: Whether to show confidence scores in messages
        """
        super().__init__()

        self.call_client = call_client
        self.bot_name = bot_name
        self.include_confidence = include_confidence

        logger.info(f"FactCheckMessengerPrebuilt initialised (bot_name: {bot_name})")

    async def process_frame(self, frame: Frame) -> AsyncGenerator[Frame, None]:
        """Process VerdictFrame and send to Daily chat.

        Args:
            frame: Input frame (VerdictFrame expected)

        Yields:
            Original frame (pass-through for logging/metrics)
        """
        if not isinstance(frame, VerdictFrame):
            yield frame
            return

        logger.info(f"Sending verdict to chat: {frame.status} - {frame.claim[:50]}...")

        try:
            # Format verdict message
            message = self._format_verdict_message(frame)

            # Send to Daily Prebuilt chat
            self.call_client.send_prebuilt_chat_message(
                message=message,
                user_name=self.bot_name
            )

            logger.debug(f"Verdict sent successfully: {frame.status}")

        except Exception as e:
            logger.error(f"Failed to send verdict to chat: {e}")
            # Don't raise - allow pipeline to continue

        # Pass frame through for potential logging/metrics
        yield frame

    def _format_verdict_message(self, verdict: VerdictFrame) -> str:
        """Format verdict into markdown message for chat.

        Args:
            verdict: VerdictFrame with claim and verification result

        Returns:
            Formatted markdown string
        """
        # Status with emoji
        emoji = self.STATUS_EMOJI.get(verdict.status, "•")
        status_text = verdict.status.upper()

        # Build message
        parts = [
            f"{emoji} **{status_text}**",
            verdict.rationale
        ]

        # Add confidence if enabled
        if self.include_confidence and verdict.confidence > 0:
            confidence_pct = int(verdict.confidence * 100)
            parts.append(f"Confidence: {confidence_pct}%")

        # Add source link if available
        if verdict.evidence_url:
            parts.append(f"[Source]({verdict.evidence_url})")

        return "\n".join(parts)


# Alternative formatter for custom message styles
class VerdictFormatter:
    """Alternative message formatters for different styles."""

    @staticmethod
    def compact(verdict: VerdictFrame) -> str:
        """Compact one-line format.

        Example: ✓ SUPPORTED: PEP 632 deprecated distutils [Source](...)
        """
        emoji = FactCheckMessengerPrebuilt.STATUS_EMOJI.get(verdict.status, "•")
        message = f"{emoji} **{verdict.status.upper()}**: {verdict.rationale}"

        if verdict.evidence_url:
            message += f" [Source]({verdict.evidence_url})"

        return message

    @staticmethod
    def detailed(verdict: VerdictFrame) -> str:
        """Detailed multi-line format with claim quoted.

        Example:
        > "Python 3.12 removed distutils"
        ✓ SUPPORTED (85%)
        PEP 632 explicitly deprecated distutils
        [Source](https://peps.python.org/pep-0632/)
        """
        emoji = FactCheckMessengerPrebuilt.STATUS_EMOJI.get(verdict.status, "•")
        lines = [
            f"> \"{verdict.claim}\"",
            f"{emoji} **{verdict.status.upper()}** ({int(verdict.confidence * 100)}%)",
            verdict.rationale
        ]

        if verdict.evidence_url:
            lines.append(f"[Source]({verdict.evidence_url})")

        return "\n".join(lines)

    @staticmethod
    def alert_only(verdict: VerdictFrame) -> str | None:
        """Only show alerts for contradicted/unclear verdicts.

        Returns:
            Message for contradicted/unclear, None for supported/not_found
        """
        if verdict.status not in ["contradicted", "unclear"]:
            return None  # Don't send message

        emoji = "⚠️" if verdict.status == "contradicted" else "⚠"
        return f"{emoji} **{verdict.status.upper()}**: {verdict.rationale}"


# Usage example in bot.py
async def create_messenger_with_client(
    room_url: str,
    token: str,
    bot_name: str = "Fact Checker"
) -> tuple[CallClient, FactCheckMessengerPrebuilt]:
    """Create CallClient and messenger (helper function).

    Args:
        room_url: Daily room URL
        token: Daily bot token
        bot_name: Bot display name

    Returns:
        Tuple of (CallClient, FactCheckMessengerPrebuilt)

    Example:
        chat_client, messenger = await create_messenger_with_client(
            room_url=os.getenv("DAILY_ROOM_URL"),
            token=os.getenv("DAILY_BOT_TOKEN")
        )
    """
    # Initialise Daily SDK
    Daily.init()

    # Create and join CallClient
    chat_client = CallClient()
    await chat_client.join(
        url=room_url,
        client_settings={"token": token}
    )

    logger.info(f"CallClient joined room: {room_url}")

    # Create messenger
    messenger = FactCheckMessengerPrebuilt(
        call_client=chat_client,
        bot_name=bot_name
    )

    return chat_client, messenger


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv
    from src.frames.custom_frames import VerdictFrame

    load_dotenv()

    async def test_messenger():
        """Test messenger with sample verdicts."""
        # Create messenger
        chat_client, messenger = await create_messenger_with_client(
            room_url=os.getenv("DAILY_ROOM_URL"),
            token=os.getenv("DAILY_BOT_TOKEN")
        )

        # Test verdicts
        test_verdicts = [
            VerdictFrame(
                claim="Python 3.12 removed distutils",
                status="supported",
                confidence=0.95,
                rationale="PEP 632 explicitly deprecated distutils in Python 3.10-3.12",
                evidence_url="https://peps.python.org/pep-0632/"
            ),
            VerdictFrame(
                claim="GDPR requires 24-hour breach notification",
                status="contradicted",
                confidence=0.90,
                rationale="Article 33 GDPR requires 72-hour notification, not 24-hour",
                evidence_url="https://gdpr-info.eu/art-33-gdpr/"
            ),
            VerdictFrame(
                claim="Kubernetes v1.30 uses eBPF by default",
                status="unclear",
                confidence=0.50,
                rationale="Documentation mentions eBPF support but default unclear",
                evidence_url="https://kubernetes.io/docs/"
            )
        ]

        # Send each verdict
        for verdict in test_verdicts:
            print(f"\nSending verdict: {verdict.status}")
            async for _ in messenger.process_frame(verdict):
                pass  # Process frame
            await asyncio.sleep(2)  # Wait between messages

        # Cleanup
        await chat_client.leave()
        Daily.deinit()
        print("\nTest complete!")

    asyncio.run(test_messenger())
```

### Step 3: Message Formatting (1 hour)

**Default format (recommended):**
```
✓ SUPPORTED
PEP 632 explicitly deprecated distutils
[Source](https://peps.python.org/pep-0632/)
```

**Compact format:**
```
✓ SUPPORTED: PEP 632 deprecated distutils [Source](...)
```

**Detailed format:**
```
> "Python 3.12 removed distutils"
✓ SUPPORTED (95%)
PEP 632 explicitly deprecated distutils
[Source](https://peps.python.org/pep-0632/)
```

**Alert-only format (only contradicted/unclear):**
```
⚠️ CONTRADICTED: Article 33 GDPR requires 72-hour notification, not 24-hour
```

Choose format based on demo preference. Default recommended for clarity.

## Daily.co CallClient API

### Initialisation
```python
from daily import Daily, CallClient

# Must call once before creating CallClient
Daily.init()

# Create client
chat_client = CallClient()
```

### Joining Room
```python
# Async join
await chat_client.join(
    url="https://your-domain.daily.co/room-name",
    client_settings={
        "token": "your_bot_token"
    }
)
```

### Sending Messages
```python
# send_prebuilt_chat_message() for Daily Prebuilt UI
chat_client.send_prebuilt_chat_message(
    message="Your message here",  # Markdown supported
    user_name="Bot Name"           # Display name
)
```

### Leaving Room
```python
# Cleanup
await chat_client.leave()
Daily.deinit()
```

## Testing Strategy

### Unit Tests
```python
"""Test fact-check messenger."""

import pytest
from unittest.mock import Mock, MagicMock
from src.processors.fact_check_messenger import FactCheckMessengerPrebuilt
from src.frames.custom_frames import VerdictFrame


def test_messenger_initialisation():
    """Test messenger initialises correctly."""
    mock_client = Mock()
    messenger = FactCheckMessengerPrebuilt(
        call_client=mock_client,
        bot_name="Test Bot"
    )

    assert messenger.call_client == mock_client
    assert messenger.bot_name == "Test Bot"


def test_message_formatting():
    """Test verdict message formatting."""
    mock_client = Mock()
    messenger = FactCheckMessengerPrebuilt(call_client=mock_client)

    verdict = VerdictFrame(
        claim="Test claim",
        status="supported",
        confidence=0.95,
        rationale="Test rationale",
        evidence_url="https://example.com"
    )

    message = messenger._format_verdict_message(verdict)

    assert "✓" in message
    assert "SUPPORTED" in message
    assert "Test rationale" in message
    assert "[Source](https://example.com)" in message


@pytest.mark.asyncio
async def test_verdict_frame_processing():
    """Test VerdictFrame processing."""
    mock_client = Mock()
    messenger = FactCheckMessengerPrebuilt(call_client=mock_client)

    verdict = VerdictFrame(
        claim="Test claim",
        status="supported",
        confidence=0.95,
        rationale="Test rationale",
        evidence_url="https://example.com"
    )

    # Process frame
    frames = []
    async for frame in messenger.process_frame(verdict):
        frames.append(frame)

    # Verify send_prebuilt_chat_message was called
    assert mock_client.send_prebuilt_chat_message.called

    # Verify frame passed through
    assert len(frames) == 1
    assert frames[0] == verdict
```

### Integration Tests (requires Daily room)
```bash
# Set up test room
uv run python src/services/daily_manager.py fact-checker-test

# Run messenger test
uv run python src/processors/fact_check_messenger.py
```

### Manual Testing Checklist
- [ ] Bot joins Daily room successfully
- [ ] Messages appear in Prebuilt chat panel
- [ ] Markdown formatting displays correctly
- [ ] Emoji appear correctly
- [ ] Links are clickable
- [ ] Multiple verdicts don't overlap
- [ ] Bot name displays correctly

## Common Issues & Solutions

### Issue 1: Messages Not Appearing
```python
# Problem: send_prebuilt_chat_message() called but no messages in chat

# Solution: Ensure CallClient joined before sending
await chat_client.join(room_url, token)  # Wait for join!
await asyncio.sleep(0.5)  # Give connection time to stabilise

# Then send messages
chat_client.send_prebuilt_chat_message(...)
```

### Issue 2: Markdown Not Rendering
```python
# Problem: Markdown shows as plain text

# Solution: Ensure Daily Prebuilt chat supports markdown (it does)
# Check message format:
message = "**Bold text**\n[Link](https://example.com)"  # ✓ Correct

# Not:
message = "<b>Bold text</b>"  # ✗ HTML not supported
```

### Issue 3: Bot Name Not Showing
```python
# Problem: Messages show "Unknown" instead of bot name

# Solution: Pass user_name parameter
chat_client.send_prebuilt_chat_message(
    message="...",
    user_name="Fact Checker"  # ← Important!
)
```

### Issue 4: Dual-Client Conflicts
```python
# Problem: DailyTransport and CallClient interfere

# Solution: Use separate connections (dual-client pattern)
# This is correct:
transport = DailyTransport(room_url, token)  # Connection 1
chat_client = CallClient()                   # Connection 2
await chat_client.join(room_url, token)      # Separate join

# Both can coexist in same room
```

## Performance Characteristics

### Latency Measurements
| Operation | Target | Typical | Notes |
|-----------|--------|---------|-------|
| Message formatting | <50ms | ~20ms | String operations |
| CallClient.send_prebuilt_chat_message() | <100ms | ~50ms | WebSocket send |
| **Total (Stage 6)** | **<150ms** | **~70ms** | Format + send |

### Resource Usage
- **Memory:** <10MB (CallClient overhead)
- **Network:** <1KB per message
- **CPU:** <5% (message formatting)

## Deliverables Checklist

- [ ] `src/processors/fact_check_messenger.py` - FactCheckMessengerPrebuilt
- [ ] DAILY_API_KEY, DAILY_ROOM_URL, DAILY_BOT_TOKEN in .env
- [ ] Daily.co room created with chat enabled
- [ ] CallClient joins room successfully
- [ ] Messages appear in Prebuilt chat
- [ ] Markdown formatting works
- [ ] Unit tests passing
- [ ] Integration test with real room successful
- [ ] Ready for full pipeline integration

## Next Steps for Integration

1. **Integrate with Pipeline:**
   - Import FactCheckMessengerPrebuilt in bot.py
   - Create CallClient instance
   - Add messenger as Stage 6 in pipeline

2. **Test End-to-End:**
   - Run full pipeline (Stages 1-6)
   - Speak test claim in Daily room
   - Verify verdict appears in chat
   - Measure total latency

3. **Refine Messaging:**
   - Choose message format (default recommended)
   - Test readability in Prebuilt UI
   - Adjust emoji/formatting if needed

4. **Demo Preparation:**
   - Test all 5 demo claims
   - Verify chat visibility
   - Screenshot verdicts for presentation

## Resources

**Daily.co Documentation:**
- Python SDK: https://docs.daily.co/reference/daily-python
- CallClient reference: https://docs.daily.co/reference/daily-python#callclient
- Prebuilt chat: https://docs.daily.co/products/prebuilt
- AI toolkit guide: https://docs.daily.co/guides/products/ai-toolkit

**Pipecat Documentation:**
- FrameProcessor: https://docs.pipecat.ai/api-reference/processors
- Dual-client pattern: https://docs.pipecat.ai/guides/daily-integration

**Project Documentation:**
- Architecture: ../architecture_design.md
- Integration: ./07_integration_layer.md
