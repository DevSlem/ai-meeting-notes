"""Audio recording functionality."""

import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import os
import threading
from typing import Optional, List


class AudioRecorder:
    """Handle audio recording with manual start/stop control."""

    def __init__(self, output_dir: str = "recordings"):
        self.output_dir = output_dir
        self.is_recording = False
        self.recording_data = []
        self.sample_rate = 44100
        self.device_id: Optional[int] = None
        self.stream = None
        os.makedirs(self.output_dir, exist_ok=True)

    def get_microphone_devices(self) -> List[str]:
        """Get list of available microphone devices."""
        devices = sd.query_devices()
        microphones = []

        for idx, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                microphones.append(f"{idx}: {device['name']}")

        return microphones

    def get_default_microphone(self) -> Optional[str]:
        """Get the default system microphone."""
        try:
            default_device = sd.query_devices(kind='input')
            if default_device:
                default_idx = default_device['index']
                return f"{default_idx}: {default_device['name']}"
        except Exception:
            pass
        return None

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for audio stream."""
        if status:
            print(f"Audio callback status: {status}")
        if self.is_recording:
            self.recording_data.append(indata.copy())

    def start_recording(self, device_idx: str, sample_rate: int = 44100) -> tuple[bool, str]:
        """Start recording audio from selected microphone."""
        try:
            if self.is_recording:
                return False, "Recording is already in progress."

            if device_idx is None or device_idx == "":
                return False, "Please select a microphone device first."

            # Extract device index from the selection string
            self.device_id = int(device_idx.split(":")[0])
            self.sample_rate = sample_rate
            self.recording_data = []
            self.is_recording = True

            # Start audio stream
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=self.device_id,
                callback=self._audio_callback,
                dtype=np.float32
            )
            self.stream.start()

            return True, "Recording started..."

        except Exception as e:
            self.is_recording = False
            return False, f"Error starting recording: {str(e)}"

    def stop_recording(self) -> tuple[Optional[str], str]:
        """Stop recording and save the audio file."""
        try:
            if not self.is_recording:
                return None, "No recording in progress."

            self.is_recording = False

            # Stop and close the stream
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None

            if len(self.recording_data) == 0:
                return None, "No audio data recorded."

            # Concatenate all recorded chunks
            recording = np.concatenate(self.recording_data, axis=0)

            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.output_dir, f"recording_{timestamp}.wav")
            sf.write(filename, recording, self.sample_rate)

            duration = len(recording) / self.sample_rate
            return filename, f"Recording stopped. Saved to {filename} (Duration: {duration:.1f}s)"

        except Exception as e:
            self.is_recording = False
            return None, f"Error stopping recording: {str(e)}"

    def get_status(self) -> str:
        """Get current recording status."""
        if self.is_recording:
            duration = sum(len(chunk) for chunk in self.recording_data) / self.sample_rate
            return f"Recording... ({duration:.1f}s)"
        return "Ready to record"
