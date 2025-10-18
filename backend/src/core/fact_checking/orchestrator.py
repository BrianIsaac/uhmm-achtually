"""Fact-checking pipeline orchestrator."""

from typing import Optional
from loguru import logger

from src.api.websocket.connection_manager import ConnectionManager
from src.api.websocket.messages import MessageFactory
from src.core.transcription.service import TranscriptionService
from src.core.nlp.sentence_aggregator import SentenceAggregator
from src.core.nlp.claim_extraction_service import ClaimExtractionService
from src.core.fact_checking.verification_service import VerificationService
from src.domain.exceptions import (
    ClaimExtractionError,
    VerificationError,
    TextProcessingError,
    MessageBroadcastError,
    SentenceAggregationError
)


class FactCheckingOrchestrator:
    """
    Orchestrates the fact-checking pipeline.

    Responsibilities:
    - Coordinate between different services
    - Handle the flow of data through the pipeline
    - Broadcast results to WebSocket clients
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        transcription_service: TranscriptionService,
        sentence_aggregator: SentenceAggregator,
        claim_extraction_service: ClaimExtractionService,
        verification_service: VerificationService
    ):
        """
        Initialize the orchestrator with required services.

        Args:
            connection_manager: WebSocket connection manager
            transcription_service: Service for handling transcriptions
            sentence_aggregator: Service for aggregating text into sentences
            claim_extraction_service: Service for extracting claims
            verification_service: Service for verifying claims
        """
        self.connection_manager = connection_manager
        self.transcription_service = transcription_service
        self.sentence_aggregator = sentence_aggregator
        self.claim_extraction_service = claim_extraction_service
        self.verification_service = verification_service
        self.message_factory = MessageFactory()

    async def process_audio_transcription(self, transcription: str) -> None:
        """
        Process a transcription from audio input.

        Args:
            transcription: The transcribed text
        """
        if not transcription or not transcription.strip():
            return

        await self.process_transcription(transcription)

    async def process_transcription(
        self,
        text: str,
        speaker: Optional[str] = None
    ) -> None:
        """
        Process a transcription through the fact-checking pipeline.

        Args:
            text: The text to process
            speaker: Optional speaker identifier
        """
        if not text or not text.strip():
            return

        speaker = speaker or "Speaker"

        # Broadcast transcript message
        try:
            transcript_message = self.message_factory.create_transcript_message(
                text=text,
                speaker=speaker,
                is_final=True
            )
            await self.connection_manager.broadcast(transcript_message)
        except Exception as e:
            # Log but don't fail - transcript display is not critical
            logger.warning(f"Failed to broadcast transcript: {e}")

        # Aggregate into sentences
        try:
            complete_sentences = self.sentence_aggregator.add_text(text)
        except Exception as e:
            raise SentenceAggregationError(
                f"Failed to aggregate text into sentences",
                {"text_length": len(text), "error": str(e)}
            )

        # Process complete sentences
        for sentence in complete_sentences:
            await self._process_sentence(sentence, speaker)

    async def _process_sentence(self, sentence: str, speaker: str) -> None:
        """
        Process a complete sentence for claims and fact-check them.

        Args:
            sentence: The sentence to process
            speaker: The speaker identifier
        """
        try:
            logger.info(f"Processing sentence: {sentence}")

            # Extract claims from the sentence
            try:
                claims = await self.claim_extraction_service.extract_claims(sentence)
            except ClaimExtractionError as e:
                logger.error(f"Claim extraction failed: {e.message}", extra=e.details)
                # Send specific error to client
                error_message = self.message_factory.create_error_message(
                    error="Failed to extract claims",
                    details=e.details
                )
                await self.connection_manager.broadcast(error_message)
                return
            except Exception as e:
                logger.error(f"Unexpected error during claim extraction: {e}", exc_info=True)
                raise ClaimExtractionError(
                    "Unexpected error during claim extraction",
                    {"sentence": sentence[:100], "error": str(e)}
                )

            if not claims:
                logger.debug("No factual claims found in sentence")
                return

            logger.info(f"Found {len(claims)} claim(s) in sentence")

            # Verify each claim
            for claim in claims:
                await self._verify_and_broadcast_claim(
                    claim=claim,
                    original_sentence=sentence,
                    speaker=speaker
                )

        except ClaimExtractionError:
            # Already handled above
            pass
        except TextProcessingError as e:
            logger.error(f"Text processing error: {e.message}", extra=e.details)
            error_message = self.message_factory.create_error_message(
                error="Text processing failed",
                details=e.details
            )
            await self.connection_manager.broadcast(error_message)
        except Exception as e:
            logger.error(f"Unexpected error processing sentence: {e}", exc_info=True)

            # Send generic error message to clients
            error_message = self.message_factory.create_error_message(
                error="Failed to process sentence",
                details={"sentence": sentence[:100], "error": str(e)}
            )

            try:
                await self.connection_manager.broadcast(error_message)
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast error message: {broadcast_error}")

    async def _verify_and_broadcast_claim(
        self,
        claim,
        original_sentence: str,
        speaker: str
    ) -> None:
        """
        Verify a claim and broadcast the verdict.

        Args:
            claim: The claim to verify
            original_sentence: The original sentence containing the claim
            speaker: The speaker identifier
        """
        try:
            # Verify the claim
            try:
                verdict = await self.verification_service.verify_claim(claim)
            except VerificationError as e:
                logger.error(f"Verification failed for claim: {e.message}", extra=e.details)
                error_message = self.message_factory.create_error_message(
                    error=f"Failed to verify claim: {e.message}",
                    details={**e.details, "claim": claim.text}
                )
                await self.connection_manager.broadcast(error_message)
                return
            except Exception as e:
                logger.error(f"Unexpected error during verification: {e}", exc_info=True)
                raise VerificationError(
                    "Unexpected error during claim verification",
                    {"claim": claim.text, "error": str(e)}
                )

            # Create and broadcast verdict message
            try:
                verdict_message = self.message_factory.from_verdict_model(
                    verdict=verdict,
                    transcript=original_sentence,
                    claim_text=claim.text,
                    speaker=speaker
                )

                successful_broadcasts = await self.connection_manager.broadcast(verdict_message)

                logger.info(
                    f"Verdict broadcast: {verdict.status} ({verdict.confidence:.2%})",
                    extra={
                        "claim": claim.text,
                        "status": verdict.status,
                        "confidence": verdict.confidence,
                        "broadcasts": successful_broadcasts
                    }
                )
            except MessageBroadcastError as e:
                logger.error(f"Failed to broadcast verdict: {e.message}", extra=e.details)
                # Don't re-throw - we've already processed the verdict
            except Exception as e:
                logger.error(f"Unexpected error broadcasting verdict: {e}", exc_info=True)
                raise MessageBroadcastError(
                    "Failed to broadcast verdict message",
                    {"claim": claim.text, "error": str(e)}
                )

        except VerificationError:
            # Already handled above
            pass
        except MessageBroadcastError:
            # Already handled above
            pass
        except Exception as e:
            logger.error(
                f"Unexpected error processing claim '{claim.text}': {e}",
                exc_info=True
            )

            # Try to send error message
            try:
                error_message = self.message_factory.create_error_message(
                    error="Failed to process claim",
                    details={"claim": claim.text, "error": str(e)}
                )
                await self.connection_manager.broadcast(error_message)
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast error message: {broadcast_error}")