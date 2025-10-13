"""AI Meeting Notes - Main entry point."""

from src.audio import AudioRecorder
from src.file_manager import AudioFileManager
from src.transcription import TranscriptionService
from src.config import SecureConfig
from src.streamlit_ui import create_streamlit_app


def main():
    """Launch the AI Meeting Notes application."""
    recorder = AudioRecorder(output_dir="recordings")
    file_manager = AudioFileManager(recordings_dir="recordings")
    transcription_service = TranscriptionService()
    config = SecureConfig(config_dir=".config")

    # Try to load saved API key
    saved_key = config.load_api_key()
    if saved_key:
        transcription_service.set_api_key(saved_key)

    # Run Streamlit app
    create_streamlit_app(recorder, file_manager, transcription_service, config)


if __name__ == "__main__":
    main()
