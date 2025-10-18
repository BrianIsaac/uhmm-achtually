"""WebSocket server with dependency injection."""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.websocket.connection_manager import ConnectionManager
from src.api.websocket.handlers import WebSocketHandler
from src.api.websocket.messages import MessageFactory
from src.core.fact_checking.orchestrator import FactCheckingOrchestrator
from src.core.transcription.service import TranscriptionService
from src.core.nlp.sentence_aggregator import SentenceAggregator
from src.core.nlp.claim_extraction_service import ClaimExtractionService
from src.core.fact_checking.verification_service import VerificationService
from src.processors.claim_extractor import ClaimExtractor
from src.processors.web_fact_checker import WebFactChecker
from src.services.stt import GroqSTT
from src.utils.config import get_settings


class WebSocketServer:
    """WebSocket server with proper dependency injection."""

    def __init__(self):
        """Initialize the WebSocket server."""
        self.settings = get_settings()
        self.connection_manager = ConnectionManager()
        self.orchestrator: Optional[FactCheckingOrchestrator] = None
        self.transcription_service: Optional[TranscriptionService] = None
        self.websocket_handler: Optional[WebSocketHandler] = None

    def _initialize_services(self) -> None:
        """Initialize all services with dependency injection."""
        logger.info("Initializing services...")

        # Initialize STT service
        stt_service = GroqSTT(
            api_key=self.settings.GROQ_API_KEY,
            model="whisper-large-v3-turbo"
        )

        # Initialize NLP services
        sentence_aggregator = SentenceAggregator()

        claim_extractor = ClaimExtractor(self.settings.GROQ_API_KEY)
        claim_extraction_service = ClaimExtractionService(claim_extractor)

        # Initialize fact-checking service
        fact_checker = WebFactChecker(
            groq_api_key=self.settings.GROQ_API_KEY,
            exa_api_key=self.settings.EXA_API_KEY,
            allowed_domains=self.settings.allowed_domains_list
        )
        verification_service = VerificationService(fact_checker)

        # Initialize transcription service
        self.transcription_service = TranscriptionService(stt_service)

        # Initialize orchestrator
        self.orchestrator = FactCheckingOrchestrator(
            connection_manager=self.connection_manager,
            transcription_service=self.transcription_service,
            sentence_aggregator=sentence_aggregator,
            claim_extraction_service=claim_extraction_service,
            verification_service=verification_service
        )

        # Set up transcription callback
        self.transcription_service.set_transcription_callback(
            self.orchestrator.process_audio_transcription
        )

        # Initialize WebSocket handler
        self.websocket_handler = WebSocketHandler(
            connection_manager=self.connection_manager,
            orchestrator=self.orchestrator
        )

        logger.info("All services initialized successfully")

    async def startup(self) -> None:
        """Start the WebSocket server and all services."""
        logger.info("Starting WebSocket server...")

        # Initialize services if not already done
        if not self.orchestrator:
            self._initialize_services()

        # Start transcription service
        if self.transcription_service:
            await self.transcription_service.start()

        logger.info("WebSocket server started successfully")

    async def shutdown(self) -> None:
        """Shut down the WebSocket server and all services."""
        logger.info("Shutting down WebSocket server...")

        # Stop transcription service
        if self.transcription_service:
            await self.transcription_service.stop()

        logger.info("WebSocket server shut down successfully")

    def create_app(self) -> FastAPI:
        """
        Create the FastAPI application with proper configuration.

        Returns:
            Configured FastAPI application
        """

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Manage application lifecycle."""
            await self.startup()
            yield
            await self.shutdown()

        app = FastAPI(
            title="Uhmm Actually Fact-Checker WebSocket Server",
            version="2.0.0",
            description="Real-time fact-checking WebSocket server with clean architecture",
            lifespan=lifespan
        )

        # Store server instance in app state for access in endpoints
        app.state.ws_server = self

        # Add CORS middleware with proper configuration
        allowed_origins = [
            "chrome-extension://*",  # Chrome extensions
            "http://localhost:3000",  # Local development
            "http://localhost:8000",  # Local API docs
        ]

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

        return app