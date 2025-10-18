"""Data models for Meeting BaaS API interactions."""

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class BotCreateRequest(BaseModel):
    """
    Request payload for creating a Meeting BaaS bot.

    Attributes:
        meeting_url: URL of the Zoom/Teams/Meet meeting to join
        bot_name: Display name for the bot participant
        recording_mode: Video recording perspective
        bot_image: Avatar image URL for the bot
        entry_message: Message sent when bot joins
        reserved: Whether to reserve bot resources in advance
        speech_to_text: Transcription configuration
        automatic_leave: Auto-leave timeout settings
    """

    meeting_url: HttpUrl = Field(..., description="Zoom/Teams/Meet meeting URL")
    bot_name: str = Field(default="Transcription Bot", description="Bot display name")
    recording_mode: Literal["speaker_view", "gallery_view", "audio_only"] = Field(
        default="audio_only", description="Recording perspective"
    )
    bot_image: HttpUrl | None = Field(
        default=None, description="Bot avatar image URL"
    )
    entry_message: str | None = Field(
        default="Hi, I'm here to transcribe this meeting.",
        description="Message when joining",
    )
    reserved: bool = Field(
        default=False, description="Reserve bot resources in advance"
    )
    speech_to_text: dict = Field(
        default={"provider": "Default"}, description="STT configuration"
    )
    automatic_leave: dict = Field(
        default={"waiting_room_timeout": 600},
        description="Auto-leave timeout in seconds",
    )


class BotCreateResponse(BaseModel):
    """
    Response from Meeting BaaS bot creation API.

    Attributes:
        bot_id: Unique identifier for the created bot
        status: Current status of the bot
        meeting_url: URL of the meeting the bot joined
    """

    bot_id: str = Field(..., description="Unique bot identifier")
    status: str = Field(..., description="Bot status")
    meeting_url: str = Field(..., description="Meeting URL")


class TranscriptWord(BaseModel):
    """
    Individual word in a transcript with timing information.

    Attributes:
        word: The transcribed word
        start: Start time offset in seconds
        end: End time offset in seconds
        confidence: Confidence score (0.0-1.0)
    """

    word: str
    start: float
    end: float
    confidence: float | None = None


class TranscriptUtterance(BaseModel):
    """
    Complete utterance from a speaker with word-level timing.

    Attributes:
        speaker: Speaker identifier or name
        text: Complete transcribed text
        start_time: Utterance start timestamp
        end_time: Utterance end timestamp
        words: List of individual words with timing
    """

    speaker: str
    text: str
    start_time: float
    end_time: float
    words: list[TranscriptWord] | None = None


class WebhookEvent(BaseModel):
    """
    Webhook event from Meeting BaaS.

    Attributes:
        event: Event type (e.g., 'meeting.started', 'meeting.completed')
        bot_id: Unique bot identifier
        meeting_url: URL of the meeting
        timestamp: Event timestamp
        data: Event-specific data payload
    """

    event: str = Field(..., description="Event type")
    bot_id: str = Field(..., description="Bot identifier")
    meeting_url: str = Field(..., description="Meeting URL")
    timestamp: str = Field(..., description="Event timestamp")
    data: dict = Field(default_factory=dict, description="Event data")


class MeetingCompleteData(BaseModel):
    """
    Data payload for meeting.completed event.

    Attributes:
        duration: Meeting duration in seconds
        recording_url: URL to access meeting recording
        transcript: List of transcript utterances
    """

    duration: float | None = None
    recording_url: str | None = None
    transcript: list[TranscriptUtterance] = Field(default_factory=list)
