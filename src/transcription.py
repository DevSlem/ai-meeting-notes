"""Audio transcription functionality using OpenAI API."""

from openai import OpenAI
from typing import Optional, Tuple, List, Callable
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor


# Model information
TRANSCRIPTION_MODELS = {
    "gpt-4o-mini-transcribe": {
        "name": "GPT-4o Mini Transcribe",
        "description": "Fast and cost-effective transcription model. Best for general use cases.",
        "price": "$0.18/hour",
        "default": True,
        "supports_verbose_json": False  # Only supports 'text' and 'json'
    },
    "gpt-4o-transcribe": {
        "name": "GPT-4o Transcribe",
        "description": "High-quality transcription with better accuracy. Ideal for complex audio.",
        "price": "$0.36/hour",
        "default": False,
        "supports_verbose_json": False  # Only supports 'text' and 'json'
    },
    "whisper-1": {
        "name": "Whisper-1",
        "description": "OpenAI's original Whisper model. Reliable and well-tested.",
        "price": "$0.36/hour",
        "default": False,
        "supports_verbose_json": True  # Supports 'verbose_json' with timestamps
    }
}


class TranscriptionService:
    """Handle audio transcription using OpenAI API."""

    def __init__(self):
        self.client: Optional[OpenAI] = None
        self.api_key: Optional[str] = None

    def set_api_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Set and validate the OpenAI API key.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not api_key or not api_key.strip():
                return False, "API key cannot be empty."

            # Remove whitespace
            api_key = api_key.strip()

            # Basic validation
            if not api_key.startswith("sk-"):
                return False, "Invalid API key format. OpenAI API keys should start with 'sk-'."

            # Try to create client and validate
            self.client = OpenAI(api_key=api_key)
            self.api_key = api_key

            return True, "API key set successfully."

        except Exception as e:
            self.client = None
            self.api_key = None
            return False, f"Error setting API key: {str(e)}"

    def is_configured(self) -> bool:
        """Check if the service is properly configured with an API key."""
        return self.client is not None and self.api_key is not None

    def _format_verbose_json(self, transcript) -> str:
        """
        Format verbose JSON response with timestamps and speaker info.

        Args:
            transcript: Verbose JSON response from OpenAI

        Returns:
            Formatted text with timestamps
        """
        output_lines = []

        # Add full text at the top
        if hasattr(transcript, 'text'):
            output_lines.append("=" * 80)
            output_lines.append("FULL TRANSCRIPTION")
            output_lines.append("=" * 80)
            output_lines.append(transcript.text)
            output_lines.append("\n" + "=" * 80)
            output_lines.append("TIMESTAMPED SEGMENTS")
            output_lines.append("=" * 80 + "\n")

        # Add segments with timestamps
        if hasattr(transcript, 'segments'):
            for segment in transcript.segments:
                # Handle both dict and object attributes
                if isinstance(segment, dict):
                    start = segment.get('start', 0)
                    end = segment.get('end', 0)
                    text = segment.get('text', '')
                else:
                    start = getattr(segment, 'start', 0)
                    end = getattr(segment, 'end', 0)
                    text = getattr(segment, 'text', '')

                # Format timestamp
                start_time = self._format_timestamp(start)
                end_time = self._format_timestamp(end)

                output_lines.append(f"[{start_time} -> {end_time}] {text}")

        return "\n".join(output_lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """
        Format seconds to MM:SS format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def transcribe_audio(
        self,
        audio_file_path: str,
        model: str = "gpt-4o-mini-transcribe",
        language: Optional[str] = None,
        timestamp_granularities: Optional[List[str]] = None,
        response_format: str = "text"
    ) -> Tuple[Optional[str], str]:
        """
        Transcribe an audio file using OpenAI API.

        Args:
            audio_file_path: Path to the audio file
            model: Model to use for transcription
            language: Optional language code (e.g., 'en', 'ko')
            timestamp_granularities: List of timestamp types ["segment", "word"]
            response_format: Response format ("text", "verbose_json", "vtt", "srt")

        Returns:
            Tuple of (transcription_text: Optional[str], status_message: str)
        """
        try:
            if not self.is_configured():
                return None, "API key not configured. Please set your OpenAI API key first."

            if not os.path.exists(audio_file_path):
                return None, "Audio file not found."

            # Check if model is valid
            if model not in TRANSCRIPTION_MODELS:
                return None, f"Invalid model: {model}"

            # Check if model supports verbose_json format
            model_info = TRANSCRIPTION_MODELS[model]
            supports_verbose = model_info.get("supports_verbose_json", False)

            # Adjust response format if model doesn't support verbose_json
            actual_format = response_format
            if response_format == "verbose_json" and not supports_verbose:
                actual_format = "text"
                print(f"Note: {model} doesn't support verbose_json format. Using 'text' format instead.")

            # Open and transcribe the audio file
            with open(audio_file_path, "rb") as audio_file:
                # Prepare transcription parameters
                transcribe_params = {
                    "file": audio_file,
                    "model": model,
                    "response_format": actual_format,
                }

                # Add language if specified
                if language:
                    transcribe_params["language"] = language

                # Add timestamp granularities only if using verbose_json
                if timestamp_granularities and actual_format == "verbose_json":
                    transcribe_params["timestamp_granularities"] = timestamp_granularities

                # Call OpenAI API
                transcript = self.client.audio.transcriptions.create(**transcribe_params)

                # Handle different response formats
                if actual_format == "text":
                    transcription_text = transcript
                elif actual_format == "verbose_json":
                    # Format verbose JSON response with timestamps
                    transcription_text = self._format_verbose_json(transcript)
                else:  # vtt, srt
                    transcription_text = transcript

                if not transcription_text:
                    return None, "Transcription returned empty result."

                return transcription_text, "Transcription completed successfully."

        except Exception as e:
            error_message = str(e)

            # Provide more specific error messages
            if "invalid_api_key" in error_message.lower():
                return None, "Invalid API key. Please check your OpenAI API key."
            elif "insufficient_quota" in error_message.lower():
                return None, "Insufficient quota. Please check your OpenAI account billing."
            elif "rate_limit" in error_message.lower():
                return None, "Rate limit exceeded. Please try again later."
            else:
                return None, f"Error during transcription: {error_message}"

    @staticmethod
    def get_model_info() -> dict:
        """Get information about available transcription models."""
        return TRANSCRIPTION_MODELS

    def transcribe_chunks_batch(
        self,
        chunk_paths: List[str],
        model: str = "gpt-4o-mini-transcribe",
        language: Optional[str] = None,
        timestamp_granularities: Optional[List[str]] = None,
        response_format: str = "text",
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[List[Optional[str]], List[str]]:
        """
        Transcribe multiple audio chunks in parallel.

        Args:
            chunk_paths: List of audio file paths
            model: Model to use for transcription
            language: Optional language code
            timestamp_granularities: List of timestamp types
            response_format: Response format
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (transcription_list, error_messages)
        """
        if not self.is_configured():
            return [], ["API key not configured"]

        total_chunks = len(chunk_paths)
        transcriptions = []
        errors = []

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=min(5, total_chunks)) as executor:
            futures = []

            for i, chunk_path in enumerate(chunk_paths):
                future = executor.submit(
                    self.transcribe_audio,
                    chunk_path,
                    model,
                    language,
                    timestamp_granularities,
                    response_format
                )
                futures.append((i, future))

            # Collect results
            for i, future in futures:
                try:
                    text, status = future.result()

                    if text:
                        transcriptions.append(text)
                        if progress_callback:
                            progress_callback(
                                i + 1,
                                total_chunks,
                                f"Completed chunk {i + 1}/{total_chunks}"
                            )
                    else:
                        transcriptions.append(None)
                        errors.append(f"Chunk {i + 1}: {status}")
                        if progress_callback:
                            progress_callback(
                                i + 1,
                                total_chunks,
                                f"Error in chunk {i + 1}/{total_chunks}"
                            )

                except Exception as e:
                    transcriptions.append(None)
                    errors.append(f"Chunk {i + 1}: {str(e)}")
                    if progress_callback:
                        progress_callback(
                            i + 1,
                            total_chunks,
                            f"Error in chunk {i + 1}/{total_chunks}"
                        )

        return transcriptions, errors

    @staticmethod
    def get_model_choices() -> list:
        """Get list of model choices for UI dropdown."""
        choices = []
        for model_id, info in TRANSCRIPTION_MODELS.items():
            label = f"{info['name']} - {info['price']}"
            if info.get('default'):
                label += " (Default)"
            choices.append((label, model_id))
        return choices
