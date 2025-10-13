"""Audio file management functionality."""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict


class AudioFileManager:
    """Manage audio files in the recordings directory."""

    def __init__(self, recordings_dir: str = "recordings"):
        self.recordings_dir = recordings_dir
        os.makedirs(self.recordings_dir, exist_ok=True)

    def save_uploaded_file(self, uploaded_file_path: str) -> Tuple[Optional[str], str]:
        """Save an uploaded audio file to the recordings directory."""
        try:
            if not uploaded_file_path or not os.path.exists(uploaded_file_path):
                return None, "No valid file provided."

            # Get file extension
            _, ext = os.path.splitext(uploaded_file_path)
            if not ext:
                ext = ".wav"

            # Create new filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_{timestamp}{ext}"
            destination = os.path.join(self.recordings_dir, filename)

            # Copy file to recordings directory
            shutil.copy2(uploaded_file_path, destination)

            return destination, f"File uploaded successfully: {filename}"

        except Exception as e:
            return None, f"Error saving file: {str(e)}"

    def list_recordings(self) -> List[Tuple[str, str, str]]:
        """
        List all audio files in the recordings directory.

        Returns:
            List of tuples: (filename, filepath, formatted_date)
        """
        recordings = []

        if not os.path.exists(self.recordings_dir):
            return recordings

        # Get all audio files
        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}

        for filename in os.listdir(self.recordings_dir):
            filepath = os.path.join(self.recordings_dir, filename)

            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filename)
                if ext.lower() in audio_extensions:
                    # Get file modification time
                    mtime = os.path.getmtime(filepath)
                    formatted_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

                    recordings.append((filename, filepath, formatted_date))

        # Sort by modification time (newest first)
        recordings.sort(key=lambda x: os.path.getmtime(x[1]), reverse=True)

        return recordings

    def delete_recording(self, filepath: str) -> Tuple[bool, str]:
        """Delete a recording file."""
        try:
            if not filepath or not os.path.exists(filepath):
                return False, "File not found."

            # Verify the file is in the recordings directory
            if not os.path.abspath(filepath).startswith(os.path.abspath(self.recordings_dir)):
                return False, "Cannot delete files outside recordings directory."

            os.remove(filepath)
            return True, "File deleted successfully."

        except Exception as e:
            return False, f"Error deleting file: {str(e)}"

    def get_file_info(self, filepath: str) -> str:
        """Get detailed information about an audio file."""
        try:
            if not os.path.exists(filepath):
                return "File not found."

            stat = os.stat(filepath)
            size_mb = stat.st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            return f"File: {os.path.basename(filepath)}\nSize: {size_mb:.2f} MB\nModified: {mtime}"

        except Exception as e:
            return f"Error getting file info: {str(e)}"

    def save_transcription(self, audio_filepath: str, transcription_text: str) -> Tuple[bool, str]:
        """
        Save transcription text for an audio file.

        Args:
            audio_filepath: Path to the audio file
            transcription_text: The transcription text to save

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not os.path.exists(audio_filepath):
                return False, "Audio file not found."

            # Create transcription filename (same name but .txt extension)
            base_name = os.path.splitext(audio_filepath)[0]
            transcription_file = f"{base_name}.txt"

            # Save transcription
            with open(transcription_file, 'w', encoding='utf-8') as f:
                f.write(transcription_text)

            return True, f"Transcription saved to {os.path.basename(transcription_file)}"

        except Exception as e:
            return False, f"Error saving transcription: {str(e)}"

    def load_transcription(self, audio_filepath: str) -> Optional[str]:
        """
        Load transcription text for an audio file.

        Args:
            audio_filepath: Path to the audio file

        Returns:
            The transcription text if found, None otherwise
        """
        try:
            base_name = os.path.splitext(audio_filepath)[0]
            transcription_file = f"{base_name}.txt"

            if not os.path.exists(transcription_file):
                return None

            with open(transcription_file, 'r', encoding='utf-8') as f:
                return f.read()

        except Exception as e:
            print(f"Error loading transcription: {e}")
            return None

    def has_transcription(self, audio_filepath: str) -> bool:
        """Check if an audio file has an associated transcription."""
        base_name = os.path.splitext(audio_filepath)[0]
        transcription_file = f"{base_name}.txt"
        return os.path.exists(transcription_file)

    def _get_metadata_filepath(self, audio_filepath: str) -> str:
        """Get the metadata file path for an audio file."""
        base_name = os.path.splitext(audio_filepath)[0]
        return f"{base_name}.json"

    def load_metadata(self, audio_filepath: str) -> Dict:
        """
        Load metadata for an audio file.

        Args:
            audio_filepath: Path to the audio file

        Returns:
            Dictionary containing metadata (empty dict if no metadata exists)
        """
        try:
            metadata_file = self._get_metadata_filepath(audio_filepath)

            if not os.path.exists(metadata_file):
                return {}

            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            print(f"Error loading metadata: {e}")
            return {}

    def save_metadata(self, audio_filepath: str, metadata: Dict) -> Tuple[bool, str]:
        """
        Save metadata for an audio file.

        Args:
            audio_filepath: Path to the audio file
            metadata: Dictionary containing metadata to save

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not os.path.exists(audio_filepath):
                return False, "Audio file not found."

            metadata_file = self._get_metadata_filepath(audio_filepath)

            # Add timestamp
            metadata['updated_at'] = datetime.now().isoformat()

            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            return True, "Metadata saved successfully."

        except Exception as e:
            return False, f"Error saving metadata: {str(e)}"

    def get_display_name(self, audio_filepath: str) -> str:
        """
        Get the display name for an audio file.
        Returns user-defined name if available, otherwise returns filename.

        Args:
            audio_filepath: Path to the audio file

        Returns:
            Display name for the file
        """
        metadata = self.load_metadata(audio_filepath)
        return metadata.get('display_name', os.path.basename(audio_filepath))

    def set_display_name(self, audio_filepath: str, display_name: str) -> Tuple[bool, str]:
        """
        Set a user-defined display name for an audio file.

        Args:
            audio_filepath: Path to the audio file
            display_name: User-defined name for the file

        Returns:
            Tuple of (success: bool, message: str)
        """
        metadata = self.load_metadata(audio_filepath)
        metadata['display_name'] = display_name.strip()
        return self.save_metadata(audio_filepath, metadata)
