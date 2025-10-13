"""Audio processing for compression and chunking."""

import os
import subprocess
import shutil
from typing import List, Tuple, Optional, Callable
from pydub import AudioSegment
import tempfile


# Compression method configurations
COMPRESSION_METHODS = {
    "recommended": {
        "name": "Recommended (Opus + Silence Removal)",
        "description": "Best for meetings. Removes silence, optimizes for speech.",
        "extension": ".opus",
        "estimated_ratio": "75-85%",
        "speed": "Medium",
        "memory": "Low",
        "ffmpeg_options": "-af silenceremove=start_periods=1:start_duration=0.1:start_threshold=-50dB:detection=peak,aformat=s16:16000:1 -c:a libopus -b:a 32k -ar 16000 -ac 1 -compression_level 10"
    },
    "fast_mp3": {
        "name": "Fast (MP3)",
        "description": "Quick compression. Standard quality.",
        "extension": ".mp3",
        "estimated_ratio": "60-70%",
        "speed": "Fast",
        "memory": "Low",
        "ffmpeg_options": "-c:a libmp3lame -b:a 32k -ar 16000 -ac 1 -q:a 9"
    },
    "balanced_opus": {
        "name": "Balanced (Opus)",
        "description": "Good compression. Efficient for speech.",
        "extension": ".opus",
        "estimated_ratio": "65-75%",
        "speed": "Medium",
        "memory": "Low",
        "ffmpeg_options": "-c:a libopus -b:a 32k -ar 16000 -ac 1"
    },
    "custom": {
        "name": "Custom",
        "description": "Specify your own FFmpeg options.",
        "extension": ".opus",  # Default, can be overridden
        "estimated_ratio": "Varies",
        "speed": "Varies",
        "memory": "Low",
        "ffmpeg_options": "-c:a libopus -b:a 32k -ar 16000 -ac 1"  # Default template
    }
}


class AudioProcessor:
    """Handle audio compression and chunking for long files."""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    def get_audio_duration(self, file_path: str) -> float:
        """
        Get audio duration in seconds.

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0  # Convert ms to seconds
        except Exception as e:
            raise Exception(f"Error getting audio duration: {str(e)}")

    def compress_audio(
        self,
        input_path: str,
        output_path: str,
        method: str = "recommended",
        custom_ffmpeg_options: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str, str]:
        """
        Compress audio file using FFmpeg (memory-efficient streaming).

        Args:
            input_path: Input audio file path
            output_path: Output audio file path
            method: Compression method ("recommended", "fast_mp3", "balanced_opus", "custom")
            custom_ffmpeg_options: Custom FFmpeg options (used when method="custom")
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (success, output_path, message)
        """
        try:
            return self._compress_with_ffmpeg(
                input_path, output_path, method,
                custom_ffmpeg_options, progress_callback
            )
        except Exception as e:
            return False, "", f"Error compressing audio: {str(e)}"

    def _compress_with_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        method: str,
        custom_ffmpeg_options: Optional[str],
        progress_callback: Optional[Callable[[str], None]]
    ) -> Tuple[bool, str, str]:
        """Compress using FFmpeg directly (memory-efficient streaming)."""
        try:
            # Check if FFmpeg is available
            if not shutil.which("ffmpeg"):
                return False, "", "FFmpeg not found. Please install FFmpeg to use compression."

            if progress_callback:
                progress_callback("Compressing with FFmpeg (streaming mode)...")

            # Get FFmpeg options based on method
            if method == "custom":
                if not custom_ffmpeg_options:
                    return False, "", "Custom FFmpeg options not provided"
                ffmpeg_options_str = custom_ffmpeg_options
            elif method in COMPRESSION_METHODS:
                ffmpeg_options_str = COMPRESSION_METHODS[method]["ffmpeg_options"]
            else:
                return False, "", f"Unknown compression method: {method}"

            # Parse FFmpeg options string into list
            import shlex
            ffmpeg_options = shlex.split(ffmpeg_options_str)

            # Construct FFmpeg command
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-i", input_path,  # Input file
            ]

            # Add parsed FFmpeg options
            cmd.extend(ffmpeg_options)

            # Add output file
            cmd.append(output_path)

            # Run FFmpeg with streaming (no memory loading)
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown FFmpeg error"
                return False, "", f"FFmpeg error: {error_msg[:200]}"

            if progress_callback:
                progress_callback("Compression complete!")

            # Calculate compression stats
            if not os.path.exists(output_path):
                return False, "", "Output file was not created"

            original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            compressed_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
            compression_ratio = (1 - compressed_size / original_size) * 100

            message = (
                f"Compressed successfully!\n"
                f"Original: {original_size:.2f} MB → Compressed: {compressed_size:.2f} MB\n"
                f"Compression: {compression_ratio:.1f}%"
            )

            return True, output_path, message

        except FileNotFoundError:
            return False, "", "FFmpeg not found. Please install FFmpeg or use 'Recommended' method."
        except Exception as e:
            return False, "", f"Compression error: {str(e)}"

    def split_audio_with_overlap(
        self,
        file_path: str,
        chunk_duration: int = 1200,
        overlap_duration: int = 30,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        """
        Split audio into overlapping chunks.

        Args:
            file_path: Path to audio file
            chunk_duration: Duration of each chunk in seconds
            overlap_duration: Overlap duration in seconds
            progress_callback: Optional callback(current, total, message)

        Returns:
            List of chunk file paths
        """
        try:
            # Load audio
            audio = AudioSegment.from_file(file_path)
            total_duration = len(audio) / 1000.0  # seconds

            if total_duration <= chunk_duration:
                # No need to split
                return [file_path]

            # Calculate chunks
            chunk_duration_ms = chunk_duration * 1000
            overlap_ms = overlap_duration * 1000
            step_ms = chunk_duration_ms - overlap_ms

            chunks = []
            chunk_paths = []

            start = 0
            chunk_index = 0

            while start < len(audio):
                end = min(start + chunk_duration_ms, len(audio))
                chunk = audio[start:end]
                chunks.append(chunk)
                start += step_ms
                chunk_index += 1

            # Save chunks to temp files
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            total_chunks = len(chunks)

            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress_callback(i + 1, total_chunks, f"Creating chunk {i + 1}/{total_chunks}...")

                chunk_path = os.path.join(
                    self.temp_dir,
                    f"{base_name}_chunk_{i:03d}.m4a"
                )

                chunk.export(chunk_path, format="ipod", codec="aac", bitrate="32k")
                chunk_paths.append(chunk_path)

            return chunk_paths

        except Exception as e:
            raise Exception(f"Error splitting audio: {str(e)}")

    def cleanup_temp_files(self, file_paths: List[str]):
        """
        Clean up temporary chunk files.

        Args:
            file_paths: List of file paths to delete
        """
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Warning: Could not delete temp file {path}: {e}")

    def merge_transcriptions(
        self,
        transcriptions: List[str],
        overlap_duration: int = 30
    ) -> str:
        """
        Merge overlapping transcriptions by removing duplicate content.

        Uses suffix-prefix matching to detect and remove overlapping text.

        Args:
            transcriptions: List of transcription texts
            overlap_duration: Overlap duration (for reference)

        Returns:
            Merged transcription text
        """
        if not transcriptions:
            return ""

        if len(transcriptions) == 1:
            return transcriptions[0]

        # Start with the first transcription
        merged = transcriptions[0].strip()

        for i in range(1, len(transcriptions)):
            current = transcriptions[i].strip()

            # Find the best overlap between the end of merged and start of current
            best_overlap_len = 0
            min_overlap_chars = 50  # Minimum characters to consider as overlap
            max_overlap_chars = min(len(merged), len(current), 3000)  # Max 3000 chars to check

            # Try to find the longest matching suffix-prefix
            for overlap_len in range(max_overlap_chars, min_overlap_chars - 1, -1):
                suffix = merged[-overlap_len:].strip()
                prefix = current[:overlap_len].strip()

                # Calculate similarity (allowing for minor differences due to transcription)
                if self._text_similarity(suffix, prefix) > 0.8:
                    best_overlap_len = overlap_len
                    break

            # If we found an overlap, skip that part in the current transcription
            if best_overlap_len > 0:
                # Remove the overlapping part from current
                current = current[best_overlap_len:].strip()

            # Add the current transcription
            if current:  # Only add if there's content left
                merged += " " + current

        return merged

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        # Simple character-based similarity
        if not text1 or not text2:
            return 0.0

        # Normalize whitespace
        text1 = " ".join(text1.split())
        text2 = " ".join(text2.split())

        # If lengths are very different, they're not similar
        len_diff = abs(len(text1) - len(text2)) / max(len(text1), len(text2))
        if len_diff > 0.3:
            return 0.0

        # Count matching characters in order
        matches = 0
        min_len = min(len(text1), len(text2))

        for i in range(min_len):
            if text1[i] == text2[i]:
                matches += 1

        return matches / min_len if min_len > 0 else 0.0
