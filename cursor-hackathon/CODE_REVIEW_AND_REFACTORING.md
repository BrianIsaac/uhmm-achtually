# Code Review and Refactoring Recommendations

## Executive Summary

This document provides a detailed code review of the WebSocket server implementation and the overall backend architecture, identifying code smells, architectural issues, and providing concrete refactoring recommendations.

## 1. Critical Issues

### 1.1 Global State Management
**Location**: `websocket_server.py:219-221`
```python
# Global instances
manager = ConnectionManager()
fact_checking_service = None
```
**Issue**: Global mutable state is an anti-pattern that makes testing difficult and can lead to race conditions.

**Recommendation**: Use dependency injection pattern:
```python
class WebSocketServer:
    def __init__(self):
        self.manager = ConnectionManager()
        self.fact_checking_service = None

    def create_app(self) -> FastAPI:
        app = FastAPI(...)
        app.state.ws_server = self
        return app
```

### 1.2 Missing Error Boundaries
**Location**: Multiple locations in `websocket_server.py`
**Issue**: Broad exception handling with generic `Exception` catches can hide bugs and make debugging difficult.

**Recommendation**: Implement specific exception types:
```python
class TranscriptionError(Exception): pass
class ClaimExtractionError(Exception): pass
class FactCheckingError(Exception): pass

# Then catch specific exceptions
try:
    verdict = await self.fact_checker.verify(claim)
except FactCheckingError as e:
    # Handle fact-checking specific errors
except httpx.TimeoutError as e:
    # Handle network timeouts
```

## 2. Architecture Issues

### 2.1 Violated Single Responsibility Principle

**FactCheckingService** class (lines 93-217) has too many responsibilities:
- WebSocket message broadcasting
- Audio processing coordination
- Sentence buffering
- Claim extraction orchestration
- Fact checking orchestration

**Recommendation**: Split into smaller, focused services:
```
src/
├── services/
│   ├── websocket/
│   │   ├── connection_manager.py
│   │   ├── message_broadcaster.py
│   │   └── client_handler.py
│   ├── audio/
│   │   ├── capture_service.py
│   │   └── transcription_service.py
│   ├── processing/
│   │   ├── sentence_aggregator.py
│   │   ├── claim_extraction_service.py
│   │   └── fact_checking_service.py
│   └── orchestration/
│       └── pipeline_orchestrator.py
```

### 2.2 Inconsistent Directory Organization

Current structure mixes different abstraction levels:
- `processors/` contains both low-level (audio) and high-level (fact checking) logic
- `services/` contains external service clients and internal services
- WebSocket server is at root level instead of in a proper module

**Recommendation**: Reorganize by domain and layer:
```
backend/
├── src/
│   ├── api/
│   │   ├── websocket/
│   │   │   ├── server.py
│   │   │   ├── handlers.py
│   │   │   └── routes.py
│   │   └── http/
│   │       ├── app.py
│   │       └── endpoints.py
│   ├── core/
│   │   ├── audio/
│   │   │   ├── capture.py
│   │   │   ├── processor.py
│   │   │   └── vad.py
│   │   ├── nlp/
│   │   │   ├── transcription.py
│   │   │   ├── claim_extraction.py
│   │   │   └── sentence_detection.py
│   │   └── fact_checking/
│   │       ├── verifier.py
│   │       └── evidence_searcher.py
│   ├── infrastructure/
│   │   ├── clients/
│   │   │   ├── groq_client.py
│   │   │   ├── exa_client.py
│   │   │   └── daily_client.py
│   │   └── config/
│   │       ├── settings.py
│   │       └── prompts.yaml
│   └── domain/
│       ├── models/
│       │   ├── claim.py
│       │   ├── verdict.py
│       │   └── transcript.py
│       └── interfaces/
│           ├── stt.py
│           └── search.py
```

## 3. Code Smells

### 3.1 Magic Numbers
**Location**: Throughout `audio_stream_processor.py`
```python
self.silence_threshold = 0.01
self.min_speech_duration = 0.5
self.max_speech_duration = 30.0
```

**Recommendation**: Move to configuration:
```python
@dataclass
class AudioConfig:
    silence_threshold: float = field(default=0.01, metadata={"description": "RMS threshold for silence"})
    min_speech_duration: float = field(default=0.5, metadata={"unit": "seconds"})
    max_speech_duration: float = field(default=30.0, metadata={"unit": "seconds"})
```

### 3.2 Duplicate Message Construction
**Location**: `websocket_server.py` lines 154-162, 196-208, 326-351

**Recommendation**: Use message factory pattern:
```python
class MessageFactory:
    @staticmethod
    def create_transcript(text: str, speaker: str = "Speaker") -> dict:
        return {
            "type": "transcript",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "text": text,
                "speaker": speaker,
                "is_final": True
            }
        }

    @staticmethod
    def create_verdict(verdict: FactCheckVerdict, sentence: str, speaker: str) -> dict:
        return {
            "type": "verdict",
            "timestamp": datetime.now().isoformat(),
            "data": verdict.to_websocket_format(sentence, speaker)
        }
```

### 3.3 Unused Imports
**Location**: `websocket_server.py`
```python
import numpy as np  # Not used
import sounddevice as sd  # Not used
from collections import deque  # Not used
```

**Recommendation**: Remove unused imports and configure linting tools.

## 4. Security Concerns

### 4.1 Overly Permissive CORS
**Location**: `websocket_server.py:249-255`
```python
allow_origins=["*"],  # Too permissive
```

**Recommendation**: Configure allowed origins properly:
```python
ALLOWED_ORIGINS = [
    "chrome-extension://*",
    "http://localhost:3000",  # Dev frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

### 4.2 No Rate Limiting
**Issue**: WebSocket connections and test endpoints have no rate limiting.

**Recommendation**: Implement rate limiting:
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/test/transcript", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def test_transcript(...):
    ...
```

### 4.3 No Input Validation
**Location**: Test endpoints accept arbitrary strings without validation.

**Recommendation**: Use Pydantic models for input validation:
```python
class TranscriptRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    speaker: str = Field(default="Test User", max_length=100)

@app.post("/test/transcript")
async def test_transcript(request: TranscriptRequest):
    ...
```

## 5. Performance Issues

### 5.1 Blocking Operations in Async Context
**Location**: `audio_stream_processor.py:64-96`
**Issue**: Audio callback runs synchronous code that could block.

**Recommendation**: Use thread pool for CPU-bound operations:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AudioStreamProcessor:
    def __init__(self, ...):
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def _process_audio_data(self, audio_data):
        loop = asyncio.get_event_loop()
        volume = await loop.run_in_executor(
            self.executor,
            lambda: np.sqrt(np.mean(audio_data ** 2))
        )
        return volume
```

### 5.2 Inefficient Connection Broadcasting
**Location**: `websocket_server.py:72-88`
**Issue**: Sequential broadcasting to all connections.

**Recommendation**: Use asyncio.gather for concurrent broadcasting:
```python
async def broadcast(self, message: dict):
    if not self.active_connections:
        return

    tasks = [
        self._send_safe(conn, message)
        for conn in self.active_connections
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Remove failed connections
    for conn, result in zip(list(self.active_connections), results):
        if isinstance(result, Exception):
            self.disconnect(conn)
```

## 6. Testing Concerns

### 6.1 No Separation of Concerns for Testing
**Issue**: Tight coupling makes unit testing difficult.

**Recommendation**: Implement interfaces and dependency injection:
```python
from abc import ABC, abstractmethod

class ITranscriptionService(ABC):
    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        pass

class IClaimExtractor(ABC):
    @abstractmethod
    async def extract(self, text: str) -> List[Claim]:
        pass

class FactCheckingService:
    def __init__(
        self,
        transcription_service: ITranscriptionService,
        claim_extractor: IClaimExtractor,
        fact_checker: IFactChecker,
        message_broadcaster: IMessageBroadcaster
    ):
        ...
```

### 6.2 No Test Fixtures
**Issue**: Test data is hardcoded in endpoints.

**Recommendation**: Create proper test fixtures:
```python
# tests/fixtures/messages.py
TEST_MESSAGES = {
    "transcript": {
        "valid": {...},
        "invalid": {...}
    },
    "verdict": {
        "supported": {...},
        "contradicted": {...}
    }
}
```

## 7. Logging and Monitoring

### 7.1 Inconsistent Logging
**Issue**: Mix of logger.info, logger.error, logger.debug without clear strategy.

**Recommendation**: Implement structured logging:
```python
import structlog

logger = structlog.get_logger()

# Use structured logging
logger.info(
    "claim_processed",
    claim_text=claim.text,
    verdict_status=verdict.status,
    confidence=verdict.confidence,
    processing_time=elapsed_time
)
```

### 7.2 No Metrics Collection
**Issue**: No performance metrics or monitoring.

**Recommendation**: Add metrics collection:
```python
from prometheus_client import Counter, Histogram, Gauge

claims_processed = Counter('claims_processed_total', 'Total claims processed')
processing_time = Histogram('claim_processing_seconds', 'Time to process claims')
active_connections = Gauge('websocket_connections_active', 'Active WebSocket connections')
```

## 8. Documentation Issues

### 8.1 Missing API Documentation
**Issue**: No OpenAPI/Swagger documentation for HTTP endpoints.

**Recommendation**: Add proper documentation:
```python
@app.post(
    "/test/transcript",
    summary="Process test transcript",
    description="Submit a test transcript for fact-checking without audio input",
    response_model=TranscriptResponse,
    responses={
        200: {"description": "Transcript processed successfully"},
        503: {"description": "Service not initialized"}
    }
)
async def test_transcript(...):
    ...
```

### 8.2 Incomplete Type Hints
**Issue**: Missing or incomplete type hints in many places.

**Recommendation**: Add comprehensive type hints:
```python
from typing import Dict, List, Optional, Set

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def broadcast(self, message: Dict[str, Any]) -> None:
        ...
```

## 9. Recommended Refactoring Priority

1. **High Priority** (Immediate):
   - Fix global state management
   - Add input validation
   - Implement proper error handling
   - Remove unused imports

2. **Medium Priority** (Next Sprint):
   - Restructure directory organization
   - Split large classes (SRP)
   - Implement message factory
   - Add rate limiting

3. **Low Priority** (Future):
   - Add metrics collection
   - Implement structured logging
   - Optimize broadcasting performance
   - Add comprehensive testing

## 10. Quick Wins

1. Remove unused imports (5 minutes)
2. Add type hints to method signatures (30 minutes)
3. Extract magic numbers to constants (15 minutes)
4. Create message factory for consistent message creation (30 minutes)
5. Add basic input validation with Pydantic (45 minutes)

## 11. Proposed New Structure

```
backend/
├── src/
│   ├── api/                    # API layer
│   │   ├── __init__.py
│   │   ├── websocket/
│   │   │   ├── __init__.py
│   │   │   ├── server.py      # FastAPI app creation
│   │   │   ├── handlers.py    # WebSocket handlers
│   │   │   ├── connection_manager.py
│   │   │   └── messages.py    # Message factory
│   │   └── http/
│   │       ├── __init__.py
│   │       ├── endpoints.py   # REST endpoints
│   │       └── models.py      # Request/Response models
│   │
│   ├── core/                   # Business logic
│   │   ├── __init__.py
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── capture.py
│   │   │   ├── processor.py
│   │   │   └── config.py
│   │   ├── transcription/
│   │   │   ├── __init__.py
│   │   │   ├── service.py
│   │   │   └── interfaces.py
│   │   ├── nlp/
│   │   │   ├── __init__.py
│   │   │   ├── claim_extractor.py
│   │   │   └── sentence_detector.py
│   │   └── fact_checking/
│   │       ├── __init__.py
│   │       ├── verifier.py
│   │       └── orchestrator.py
│   │
│   ├── infrastructure/         # External services
│   │   ├── __init__.py
│   │   ├── groq/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── stt_service.py
│   │   ├── exa/
│   │   │   ├── __init__.py
│   │   │   └── search_client.py
│   │   └── daily/
│   │       ├── __init__.py
│   │       └── transport.py
│   │
│   ├── domain/                 # Domain models
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── claim.py
│   │   │   ├── verdict.py
│   │   │   └── transcript.py
│   │   └── exceptions/
│   │       ├── __init__.py
│   │       └── custom_exceptions.py
│   │
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── config.py
│       ├── logging.py
│       └── metrics.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   └── run_websocket_server.sh
│
├── config/
│   ├── prompts.yaml
│   └── settings.yaml
│
└── main.py                     # Entry point
```

## Conclusion

The codebase shows good functionality but needs significant refactoring to improve maintainability, testability, and scalability. Focus on high-priority items first, particularly around state management, error handling, and code organization. The proposed structure follows Domain-Driven Design principles and clean architecture patterns, which will make the codebase more maintainable and testable in the long run.