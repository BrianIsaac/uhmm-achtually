# Uhmm Achtually - Real-time AI Fact Checker

A real-time fact-checking system that listens to voice conversations, extracts factual claims, and verifies them using web search and AI. Built with Python, PydanticAI, and Pipecat for voice processing.

## Features

- **Real-time Voice Processing**: Captures voice input via Daily.co
- **Automatic Claim Extraction**: Uses AI to identify factual claims in conversations
- **Web-based Verification**: Searches trusted sources to verify claims
- **Confidence Scoring**: Provides confidence levels for each verdict
- **Fast Response**: Sub-500ms search latency for quick fact-checking

## Architecture

```
Voice Input (Daily.co) → STT (Groq) → Claim Extraction → Web Search (Exa) → Verification (Groq) → Results
                ↓
        System Audio → WebSocket Server → Chrome Extension
```

### Core Components

1. **Voice Input**: Daily.co transport for real-time audio capture
2. **Speech-to-Text**: Groq STT with Whisper model
3. **Claim Extraction**: PydanticAI agent to identify factual claims
4. **Web Search**: Exa API for fast neural/keyword search
5. **Verification**: PydanticAI agent to analyze evidence and generate verdicts
6. **WebSocket Server**: FastAPI server with clean architecture and dependency injection

### Architecture Principles

The WebSocket server follows clean architecture principles:
- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Injection**: Services are injected, not hardcoded
- **Layered Architecture**: Clear separation between API, Core, and Infrastructure layers
- **Message Factory Pattern**: Consistent message creation across the application

## Project Structure

```
uhmm-achtually/
├── backend/
│   ├── main.py                          # Main entry point for WebSocket server
│   ├── bot.py                          # Daily.co voice-enabled fact checker
│   ├── test_websocket_client.py        # WebSocket test client
│   ├── run_websocket_server.sh         # Server startup script
│   ├── src/
│   │   ├── api/                        # API layer
│   │   │   ├── websocket/
│   │   │   │   ├── server.py           # WebSocket server with DI
│   │   │   │   ├── connection_manager.py # Connection management
│   │   │   │   ├── handlers.py         # Message handlers
│   │   │   │   └── messages.py         # Message factory
│   │   │   └── http/
│   │   │       └── endpoints.py        # REST API endpoints
│   │   ├── core/                       # Business logic
│   │   │   ├── fact_checking/
│   │   │   │   ├── orchestrator.py     # Pipeline orchestration
│   │   │   │   └── verification_service.py # Claim verification
│   │   │   ├── nlp/
│   │   │   │   ├── sentence_aggregator.py # Text processing
│   │   │   │   └── claim_extraction_service.py # Claim extraction
│   │   │   └── transcription/
│   │   │       └── service.py          # Audio transcription
│   │   ├── models/
│   │   │   ├── claim_models.py         # Pydantic models for claims
│   │   │   └── verdict_models.py       # Pydantic models for verdicts
│   │   ├── processors/
│   │   │   ├── audio_stream_processor.py # Audio capture
│   │   │   ├── claim_extractor.py      # PydanticAI claim extraction
│   │   │   └── web_fact_checker.py     # Web-based verification
│   │   ├── services/
│   │   │   ├── exa_client.py           # Exa search API
│   │   │   └── stt/
│   │   │       ├── groq_stt.py         # Groq STT service
│   │   │       └── avalon_stt.py       # Avalon STT service
│   │   └── utils/
│   │       └── config.py               # Configuration
│   ├── config/
│   │   └── prompts.yaml                # AI agent prompts
│   ├── dev_config.yaml                 # Development configuration
│   └── .env                             # Environment variables
├── cursor-hackathon/
│   └── WEBSOCKET_API_SPEC.md           # WebSocket API specification
└── README.md
```

## Setup

### Prerequisites

- Python 3.12+
- Groq API key for STT and LLM
- Exa API key for web search
- (Optional) Daily.co account - only needed for `bot.py` (remote meetings)
- (Optional) Avalon API key for alternative STT

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/uhmm-achtually.git
cd uhmm-achtually
```

2. Install UV package manager (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Create and activate virtual environment:
```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Install dependencies:
```bash
# For WebSocket server (Chrome extension support)
uv pip install -e ".[llm,search,stt,config,utils,websocket,dev]"

# For Daily.co bot (remote meetings) - requires additional pipecat dependencies
uv pip install -e ".[llm,search,stt,config,utils,dev]"
uv pip install "pipecat-ai[daily,silero]>=0.0.90"
```

5. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
# Required APIs
GROQ_API_KEY=your_groq_api_key
EXA_API_KEY=your_exa_api_key

# Optional - Only needed for bot.py (Daily.co meetings)
DAILY_API_KEY=your_daily_api_key
DAILY_ROOM_URL=https://your-domain.daily.co/your-room
DAILY_BOT_TOKEN=optional_bot_token

# Optional - Alternative STT provider
AVALON_API_KEY=optional_avalon_key

# Configuration
ALLOWED_DOMAINS=docs.python.org,kubernetes.io,owasp.org,nist.gov,postgresql.org
PYTHON_ENV=development
LOG_LEVEL=INFO
```

## Usage

### Running the Bot (Daily.co Voice Input)

```bash
cd backend
uv run bot.py
```

The bot will:
1. Join the Daily.co room specified in DAILY_ROOM_URL
2. Listen for voice input
3. Process speech and extract claims
4. Fact-check claims in real-time
5. Log results to the console

### Running the WebSocket Server (For Chrome Extension)

```bash
cd backend
./run_websocket_server.sh
```

Or manually:
```bash
uvicorn main:app --host localhost --port 8765 --reload
```

The WebSocket server will:
1. Start on `ws://localhost:8765`
2. Capture system audio
3. Transcribe speech in real-time
4. Extract and verify claims
5. Send transcripts and verdicts to connected Chrome extension

### Testing the WebSocket Server

```bash
python backend/test_websocket_client.py
```

This will send test transcripts and display the fact-checking results.

### Example Output

```
========================================================================
VOICE-ENABLED PYDANTIC-AI FACT-CHECKER
Listening for voice input -> Processing with PydanticAI
========================================================================
Joining room: https://your-domain.daily.co/your-room
Ready to listen! Speak into your microphone...

VOICE INPUT: Python 3.12 removed the distutils package.
Complete sentence: Python 3.12 removed the distutils package.
============================================================
PROCESSING: Python 3.12 removed the distutils package.
============================================================
Extracting claims with PydanticAI...
Found 1 claim(s)
   - Python 3.12 removed the distutils package (type: software)

Fact-checking with PydanticAI...
Claim 1: Python 3.12 removed the distutils package
   Status: supported
   Confidence: 95.00%
   Rationale: Python 3.12 officially removed the distutils package as part of PEP 632.
   Evidence: https://docs.python.org/3.12/whatsnew/3.12.html
============================================================
```

## Configuration

### dev_config.yaml

```yaml
# VAD (Voice Activity Detection)
vad:
  disable: false
  start_secs: 0.2
  stop_secs: 0.2
  min_volume: 0.6

# Speech-to-Text
stt:
  provider: groq  # or avalon
  groq:
    model: whisper-large-v3-turbo
    language: en
  avalon:
    model: avalon-1
    language: en

# LLM Configuration
llm:
  claim_extraction_model: llama-3.3-70b-versatile
  verification_model: llama-3.3-70b-versatile
  temperature: 0.1

# Logging
logging:
  level: INFO
  log_transcriptions: true
```

### STT Provider Selection

The system supports two STT providers:

1. **Groq STT** (default) - Fast, reliable Whisper-based transcription
2. **Avalon STT** - Alternative provider with developer-optimized transcription

To switch providers, modify `dev_config.yaml`:
```yaml
stt:
  provider: avalon  # Switch from 'groq' to 'avalon'
```

### Allowed Domains

The fact-checker searches only trusted domains specified in ALLOWED_DOMAINS. Default domains include:
- docs.python.org (Python documentation)
- kubernetes.io (Kubernetes docs)
- owasp.org (Security best practices)
- nist.gov (Standards and guidelines)
- postgresql.org (PostgreSQL documentation)

## Development

### Running Tests

```bash
cd backend
uv run pytest tests/
```

### Adding New Domains

Update the ALLOWED_DOMAINS environment variable in `.env`:

```env
ALLOWED_DOMAINS=docs.python.org,stackoverflow.com,developer.mozilla.org
```

### Customizing Prompts

Edit `backend/config/prompts.yaml` to customize AI agent behavior:

```yaml
claim_extraction:
  system_prompt: "Your custom claim extraction instructions..."
  user_prompt_template: "Extract claims from: {text}"

fact_verification:
  system_prompt: "Your custom verification instructions..."
  user_prompt_template: "Verify this claim: {claim_text}\nEvidence: {passages}"
```

## API Performance

- **Exa Search**: < 500ms latency (keyword mode)
- **Groq STT**: ~200-400ms for short utterances
- **Claim Extraction**: ~200-300ms
- **Verification**: ~500-800ms
- **Total Pipeline**: ~1.5-2.5 seconds end-to-end

## Architecture Details

### Voice Processing Flow

1. **Audio Capture**: Daily.co WebRTC transport captures microphone audio
2. **VAD**: Silero VAD detects speech segments
3. **STT**: Groq/Avalon converts speech to text
4. **Sentence Buffering**: Accumulates text until sentence boundary detected
5. **Claim Extraction**: PydanticAI analyzes sentence for factual claims
6. **Web Search**: Exa searches trusted domains for evidence
7. **Verification**: PydanticAI analyzes evidence and generates verdict

### Key Design Decisions

- **PydanticAI**: Ensures structured, consistent AI outputs
- **Keyword Search**: Prioritizes speed over neural search quality
- **Domain Filtering**: Limits search to trusted sources for reliability
- **Inline Processing**: Simplified architecture without complex pipelines

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [PydanticAI](https://github.com/pydantic/pydantic-ai) for structured AI outputs
- [Pipecat](https://github.com/pipecat-ai/pipecat) for real-time audio processing
- [Exa](https://exa.ai) for fast neural search
- [Groq](https://groq.com) for LLM and STT services
- [Daily.co](https://daily.co) for WebRTC infrastructure
- [Avalon](https://avalon.ai) for alternative STT services