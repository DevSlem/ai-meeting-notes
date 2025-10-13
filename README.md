# AI Meeting Notes

A Streamlit-based application for recording, managing, and transcribing meeting audio using OpenAI's Whisper API.

## Features

- 🎙️ **Audio Recording & Upload**: Record from microphone or upload audio files (WAV, MP3, M4A, FLAC, OGG, WebM)
- 📝 **AI Transcription**: Multiple OpenAI models (GPT-4o Mini, GPT-4o, Whisper-1) with automatic language detection
- 🗂️ **File Management**: Custom naming, metadata system, integrated playback, and transcription viewing
- 📦 **Smart Compression**: Automatic compression for large files (>25MB) or long audio (>20min)
- ⚡ **Long Audio Support**: Automatic chunking and parallel processing for files over 20 minutes
- 🔒 **Secure Storage**: Local storage with encrypted API key management

## Prerequisites

- **Python 3.12+**
- **FFmpeg**: `brew install ffmpeg` (macOS) or `sudo apt-get install ffmpeg` (Ubuntu)
- **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- **uv Package Manager**: [Install uv](https://github.com/astral-sh/uv)

## Installation

```bash
# Install dependencies
uv sync

# Run application
streamlit run main.py
```

The app opens at `http://localhost:8501`.

## Quick Start

1. **Setup API Key**: Click ⚙️ API Key Settings → Enter OpenAI API key → Save
2. **Record/Upload**: Navigate to "Record & Upload" tab
3. **Manage**: Go to "Recordings" tab to view all files
4. **Transcribe**: Click 🎙️ button next to any recording
5. **Rename**: Click ✏️ to set custom names (e.g., "AI Meeting")

## Usage

### Recording Audio
1. Select microphone and sample rate (16kHz recommended)
2. Click 🔴 Start Recording → Speak → ⏹️ Stop Recording
3. File saved automatically to `recordings/` directory

> [!NOTE]
> If you want to record your system audio (e.g., Zoom calls), use a virtual audio device like [BlackHole (macOS)](https://github.com/ExistentialAudio/BlackHole) or [VB-Audio Virtual Cable (Windows)](https://vb-audio.com/Cable/).

### Transcribing Audio
1. Click 🎙️ button in Recordings tab
2. Select model (GPT-4o Mini recommended for most cases)
3. Configure advanced options if needed:
   - **Compression**: Auto-enabled for large/long files
   - **Chunk Overlap**: 30s default (adjustable 15-120s)
   - **Language**: Auto-detect or specify (en, ko, ja, etc.)
4. Click Start Transcription
5. View results in scrollable text area

### Custom Naming
1. Click ✏️ button next to recording
2. Enter meaningful name (e.g., "Weekly Team Meeting")
3. Original filename preserved, display name stored in `<filename>.json`

## Compression Methods

| Method | Ratio | Speed | Use Case |
|--------|-------|-------|----------|
| **Recommended** | 75-85% | Medium | Meetings with silence removal |
| **Fast (MP3)** | 60-70% | Fast | Quick compression |
| **Balanced (Opus)** | 65-75% | Medium | Efficient for speech |
| **Custom** | Varies | Varies | Specify your own FFmpeg options |

Compression **auto-enabled** when file >25MB or duration >20min.

> [!NOTE]
> The ratio is arbitrary and depends on the audio content.

## API Models & Pricing

Transcription models:

| Model | Price/hour | Best For |
|-------|------------|----------|
| `gpt-4o-mini-transcribe` | $0.18 | Most meetings (recommended) |
| `gpt-4o-transcribe` | $0.36 | Complex audio, heavy accents |
| `whisper-1` | $0.36 | When timestamps needed |

## File Structure

```
recordings/
├── recording_20251013_145550.wav      # Audio file
├── recording_20251013_145550.json     # Metadata (display name)
└── recording_20251013_145550.txt      # Transcription
```

## Troubleshooting

**FFmpeg not found**: Install with `brew install ffmpeg` (macOS) or `sudo apt-get install ffmpeg` (Ubuntu)

**API key issues**: Click ⚙️ API Key Settings and verify your key at [OpenAI Platform](https://platform.openai.com/api-keys)

**Dialog not closing**: Use Close/Done buttons instead of X button

**Long files**: App automatically chunks files >23min with intelligent merging

## Tips

- Let app auto-decide compression (enabled only when beneficial)
- Use GPT-4o Mini for most meetings
- Rename recordings immediately for easy identification
- Monitor API usage at [OpenAI Usage Dashboard](https://platform.openai.com/usage)

---

**Built with Streamlit, OpenAI Whisper API, and FFmpeg**
