"""Streamlit web UI for AI Meeting Notes."""

import streamlit as st
import os
import tempfile
from src.audio import AudioRecorder
from src.file_manager import AudioFileManager
from src.transcription import TranscriptionService
from src.config import SecureConfig
from src.audio_processor import AudioProcessor, COMPRESSION_METHODS


def init_session_state(
    recorder: AudioRecorder,
    file_manager: AudioFileManager,
    transcription_service: TranscriptionService,
    config: SecureConfig
):
    """Initialize Streamlit session state."""
    if 'recorder' not in st.session_state:
        st.session_state.recorder = recorder
    if 'file_manager' not in st.session_state:
        st.session_state.file_manager = file_manager
    if 'transcription_service' not in st.session_state:
        st.session_state.transcription_service = transcription_service
    if 'config' not in st.session_state:
        st.session_state.config = config
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False


def page_record_and_upload():
    """Record & Upload page."""
    st.header("🎤 Record or Upload Audio")

    recorder = st.session_state.recorder
    file_manager = st.session_state.file_manager

    # Recording Section
    with st.expander("🔴 Direct Recording", expanded=True):
        st.markdown("Select your microphone and record audio.")

        # Microphone selection
        mic_devices = recorder.get_microphone_devices()
        default_mic = recorder.get_default_microphone()

        default_index = 0
        if default_mic and default_mic in mic_devices:
            default_index = mic_devices.index(default_mic)

        selected_mic = st.selectbox(
            "Select Microphone",
            options=mic_devices,
            index=default_index,
            help="Choose the microphone device to use for recording"
        )

        # Sample rate selection
        sample_rate = st.radio(
            "Sample Rate (Hz)",
            options=[16000, 44100, 48000],
            index=0,
            horizontal=True,
            help="Higher sample rate = better quality but larger file size"
        )

        # Recording controls
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔴 Start Recording", disabled=st.session_state.is_recording, use_container_width=True):
                success, message = recorder.start_recording(selected_mic, sample_rate)
                if success:
                    st.session_state.is_recording = True
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with col2:
            if st.button("⏹️ Stop Recording", disabled=not st.session_state.is_recording, use_container_width=True):
                audio_file, message = recorder.stop_recording()
                st.session_state.is_recording = False
                if audio_file:
                    # Store the completed audio file info for display
                    st.session_state.last_recorded_file = audio_file
                    st.session_state.show_last_recording = True
                    st.success(f"{message}\n\n→ Go to Recordings tab to view your file.")
                else:
                    st.error(message)

        if st.session_state.is_recording:
            st.info("🔴 Recording in progress...")

        # Show last recorded audio if available
        if st.session_state.get('show_last_recording', False) and st.session_state.get('last_recorded_file'):
            st.markdown("**Last Recording:**")
            try:
                with open(st.session_state.last_recorded_file, 'rb') as f:
                    audio_bytes = f.read()
                    st.audio(audio_bytes, format='audio/wav')
                if st.button("🗑️ Clear Preview", use_container_width=True):
                    st.session_state.show_last_recording = False
                    st.session_state.last_recorded_file = None
                    st.rerun()
            except Exception as e:
                st.warning(f"⚠️ Could not load recording: {str(e)}")
                st.session_state.show_last_recording = False

    # Upload Section
    with st.expander("📤 Upload Audio File", expanded=True):
        st.markdown("Upload an existing audio file to your recordings.")

        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['wav', 'mp3', 'm4a', 'flac', 'ogg', 'webm'],
            help="Upload an audio file to save to recordings"
        )

        if st.button("💾 Save Upload", disabled=uploaded_file is None, use_container_width=True):
            if uploaded_file:
                # Save to temp file first
                temp_path = f"/tmp/{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                filepath, message = file_manager.save_uploaded_file(temp_path)
                if filepath:
                    st.success(f"{message}\n\n→ Go to Browse Recordings to view your file.")
                    # Clean up temp file
                    try:
                        os.remove(temp_path)
                    except:
                        pass
                else:
                    st.error(message)


@st.dialog("⚙️ API Key Settings", width="large")
def show_api_key_dialog():
    """Show API key configuration dialog."""
    transcription_service = st.session_state.transcription_service
    config = st.session_state.config

    st.markdown("**OpenAI API Key Setup**")
    st.markdown("Your API key is stored securely and never exposed in the UI.")

    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Enter your OpenAI API key (starts with 'sk-')"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Save API Key", use_container_width=True):
            if api_key_input:
                success, message = transcription_service.set_api_key(api_key_input)
                if success:
                    if config.save_api_key(api_key_input):
                        st.success(f"✓ {message}\nAPI key saved securely.")
                        st.session_state.show_api_dialog = False
                        st.rerun()
                    else:
                        st.warning(f"✓ {message}\n⚠ Warning: Could not save to file.")
                else:
                    st.error(f"✗ {message}")
            else:
                st.error("Please enter an API key.")

    with col2:
        if st.button("🗑️ Delete API Key", use_container_width=True):
            if config.delete_api_key():
                transcription_service.client = None
                transcription_service.api_key = None
                st.success("API key deleted successfully.")
                st.session_state.show_api_dialog = False
                st.rerun()
            else:
                st.error("Failed to delete API key.")

    with col3:
        if st.button("✕ Close", use_container_width=True):
            st.session_state.show_api_dialog = False
            st.rerun()

    # Show current status
    if transcription_service.is_configured():
        st.success("✓ API key is configured and ready to use.")
    else:
        st.warning("⚠ No API key configured. Please enter your OpenAI API key above.")


@st.dialog("✏️ Rename Recording")
def show_rename_dialog(filepath):
    """Show dialog to rename a recording."""
    file_manager = st.session_state.file_manager

    current_display_name = file_manager.get_display_name(filepath)
    filename = os.path.basename(filepath)

    st.markdown(f"**File:** {filename}")

    new_name = st.text_input(
        "Display Name",
        value=current_display_name if current_display_name != filename else "",
        placeholder="e.g., AI Meeting, Interview Notes",
        help="Enter a custom name for this recording"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Save", type="primary", use_container_width=True):
            if new_name and new_name.strip():
                success, message = file_manager.set_display_name(filepath, new_name.strip())
                if success:
                    st.success("✓ Name updated successfully!")
                    st.session_state.show_rename_dialog = False
                    if 'editing_file' in st.session_state:
                        del st.session_state.editing_file
                    st.rerun()
                else:
                    st.error(f"✗ {message}")
            else:
                st.warning("⚠ Please enter a name.")

    with col2:
        if st.button("✕ Cancel", use_container_width=True):
            st.session_state.show_rename_dialog = False
            if 'editing_file' in st.session_state:
                del st.session_state.editing_file
            st.rerun()


@st.dialog("🎙️ Transcribe Audio", width="large")
def show_transcribe_dialog(filepath, filename):
    """Show transcription dialog for a specific recording."""
    transcription_service = st.session_state.transcription_service
    file_manager = st.session_state.file_manager

    # Check if we have a completed transcription result to display
    if st.session_state.get('transcription_completed', False):
        st.markdown(f"**File:** {filename}")

        # Display the saved result
        result = st.session_state.get('transcription_result', {})

        if result.get('success'):
            st.success("✓ Transcription completed successfully.")

            st.markdown("### 📄 Transcription Result")
            st.text_area(
                "Transcription:",
                value=result.get('text', ''),
                height=400,
                label_visibility="collapsed"
            )
        else:
            st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
            if result.get('traceback'):
                st.code(result['traceback'])

        st.markdown("---")
        # Done button - clear all state
        if st.button("✓ Done - Return to Recordings", type="primary", use_container_width=True):
            # Clear all transcription-related state
            st.session_state.transcription_completed = False
            st.session_state.transcription_result = {}
            st.session_state.show_transcribe_dialog = False
            if 'current_transcribe_file' in st.session_state:
                del st.session_state.current_transcribe_file
            st.rerun()
        return

    st.markdown(f"**File:** {filename}")

    # Check if API key is configured
    if not transcription_service.is_configured():
        st.error("❌ API key not configured. Please set up your API key first.")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("⚙️ Open API Key Settings", use_container_width=True):
                st.session_state.show_api_dialog = True
                st.session_state.show_transcribe_dialog = False
                if 'current_transcribe_file' in st.session_state:
                    del st.session_state.current_transcribe_file
                st.rerun()

        with col2:
            if st.button("✕ Close", use_container_width=True):
                st.session_state.show_transcribe_dialog = False
                if 'current_transcribe_file' in st.session_state:
                    del st.session_state.current_transcribe_file
                st.rerun()
        return

    # Model selection
    from src.transcription import TRANSCRIPTION_MODELS

    model_options = {f"{info['name']} - {info['price']}": model_id
                     for model_id, info in TRANSCRIPTION_MODELS.items()}

    selected_model_label = st.selectbox(
        "Select Model",
        options=list(model_options.keys()),
        index=0
    )
    selected_model_id = model_options[selected_model_label]

    # Language
    language = st.text_input(
        "Language Code (optional)",
        placeholder="e.g., en, ko, ja",
        help="Leave empty for auto-detection"
    )

    # Check file size and duration to determine if compression is needed
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    audio_processor = AudioProcessor()
    try:
        duration_seconds = audio_processor.get_audio_duration(filepath)
    except:
        duration_seconds = 0

    # Auto-determine compression need
    # OpenAI API limit: 25MB max file size
    # Chunking threshold: 1400 seconds (23 min 20 sec)
    needs_compression = file_size_mb > 25 or duration_seconds > 1200  # 20 minutes

    # Advanced options
    with st.expander("⚙️ Advanced Options", expanded=False):
        st.markdown("**Audio Processing**")

        # Show file info
        st.info(f"📊 File size: {file_size_mb:.2f} MB | Duration: {duration_seconds:.1f}s ({duration_seconds/60:.1f} min)")

        if needs_compression:
            st.warning(f"⚠️ Compression recommended: File is {'large (>25MB)' if file_size_mb > 25 else 'long (>20min)'}")
            compress_audio_default = True
        else:
            st.success("✓ File is small and short enough - compression optional")
            compress_audio_default = False

        compress_audio = st.checkbox(
            "Compress audio before transcription",
            value=compress_audio_default,
            help="Automatically enabled for large files (>25MB) or long audio (>20min). OpenAI API has 25MB limit."
        )

        # Compression method selection
        compression_method = "recommended"
        custom_ffmpeg_options = None

        if compress_audio:
            st.markdown("**Compression Method**")

            method_options = {}
            for key, info in COMPRESSION_METHODS.items():
                label = f"{info['name']}"
                method_options[label] = key

            selected_method_label = st.radio(
                "Select compression method:",
                options=list(method_options.keys()),
                index=0,
                help="Choose based on your needs: quality vs speed vs memory usage"
            )
            compression_method = method_options[selected_method_label]

            # Show detailed info
            method_info = COMPRESSION_METHODS[compression_method]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Est. Compression", method_info['estimated_ratio'])
            with col2:
                st.metric("Speed", method_info['speed'])
            with col3:
                st.metric("Memory", method_info['memory'])

            st.caption(f"ℹ️ {method_info['description']}")

            # Show FFmpeg options
            st.markdown("**FFmpeg Options**")

            if compression_method == "custom":
                custom_ffmpeg_options = st.text_input(
                    "Custom FFmpeg options:",
                    value=method_info['ffmpeg_options'],
                    help="Specify your own FFmpeg options"
                )
                st.info("💡 The final command will be: `ffmpeg -y -i input.wav [your options] output.opus`")
            else:
                st.code(method_info['ffmpeg_options'], language="bash")
                st.caption("📋 These are the FFmpeg options that will be used.")

        chunk_overlap = st.slider(
            "Chunk overlap duration (seconds)",
            min_value=15,
            max_value=120,
            value=30,
            step=15,
            help="Overlap between chunks for long audio files."
        )

        st.markdown("---")
        st.markdown("**Transcription Features**")

        enable_timestamps = st.checkbox(
            "Enable timestamps",
            value=False,
            help="Add timestamps to transcription (segment-level). Only supported by Whisper-1 model."
        )

    # Buttons at the bottom
    col1, col2 = st.columns(2)

    with col1:
        start_transcription = st.button("🎙️ Start Transcription", type="primary", use_container_width=True)

    with col2:
        if st.button("✕ Close", use_container_width=True):
            st.session_state.show_transcribe_dialog = False
            if 'current_transcribe_file' in st.session_state:
                del st.session_state.current_transcribe_file
            st.rerun()

    # Transcribe button logic
    if start_transcription:
        # Perform transcription (code from page_transcribe)
        language_code = language.strip() if language and language.strip() else None

        # Determine transcription format
        if enable_timestamps:
            response_format = "verbose_json"
            timestamp_granularities = ["segment"]
        else:
            response_format = "text"
            timestamp_granularities = None

        try:
            # Use already computed duration
            duration = duration_seconds
            st.info(f"📊 Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

            needs_chunking = duration > 1400

            processed_file = filepath
            chunk_paths = []

            # Step 1: Compression
            if compress_audio:
                st.markdown("### 📦 Step 1: Compressing Audio")
                status_placeholder = st.empty()

                def compression_progress(message):
                    status_placeholder.text(message)

                method_info = COMPRESSION_METHODS[compression_method]
                file_extension = method_info['extension']

                compressed_path = os.path.join(
                    tempfile.gettempdir(),
                    f"compressed_{os.path.splitext(os.path.basename(filepath))[0]}{file_extension}"
                )

                success, output_path, message = audio_processor.compress_audio(
                    filepath,
                    compressed_path,
                    method=compression_method,
                    custom_ffmpeg_options=custom_ffmpeg_options,
                    progress_callback=compression_progress
                )

                if success:
                    st.success(message)
                    processed_file = output_path
                else:
                    st.error(message)
                    return

            # Step 2: Chunking
            if needs_chunking:
                st.markdown("### ✂️ Step 2: Splitting into Overlapping Chunks")
                st.info(f"🔪 Audio is too long ({duration:.0f}s > 1400s). Splitting into chunks with {chunk_overlap}-second overlaps...")

                chunk_progress = st.progress(0)
                chunk_status = st.empty()

                def chunking_progress(current, total, message):
                    chunk_status.text(message)
                    chunk_progress.progress(current / total)

                chunk_paths = audio_processor.split_audio_with_overlap(
                    processed_file,
                    chunk_duration=1200,
                    overlap_duration=chunk_overlap,
                    progress_callback=chunking_progress
                )

                st.success(f"✅ Split into {len(chunk_paths)} chunks")
            else:
                chunk_paths = [processed_file]

            # Step 3: Transcription
            st.markdown("### 🎙️ Step 3: Transcribing Audio")

            if len(chunk_paths) > 1:
                st.info(f"📝 Processing {len(chunk_paths)} chunks in parallel...")

                trans_progress = st.progress(0)
                trans_status = st.empty()

                def transcription_progress(current, total, message):
                    trans_status.text(message)
                    trans_progress.progress(current / total)

                transcriptions, errors = transcription_service.transcribe_chunks_batch(
                    chunk_paths,
                    selected_model_id,
                    language_code,
                    timestamp_granularities,
                    response_format,
                    progress_callback=transcription_progress
                )

                if errors:
                    st.warning(f"⚠️ Some chunks had errors:\n" + "\n".join(errors))

                valid_transcriptions = [t for t in transcriptions if t is not None]

                if valid_transcriptions:
                    transcription_text = audio_processor.merge_transcriptions(valid_transcriptions)
                    st.success(f"✅ Successfully transcribed {len(valid_transcriptions)}/{len(chunk_paths)} chunks")
                else:
                    st.error("❌ All chunks failed to transcribe")
                    transcription_text = None

            else:
                with st.spinner("Transcribing..."):
                    transcription_text, status_message = transcription_service.transcribe_audio(
                        chunk_paths[0],
                        selected_model_id,
                        language_code,
                        timestamp_granularities,
                        response_format
                    )

                if transcription_text:
                    st.success(f"✓ {status_message}")
                else:
                    st.error(f"✗ {status_message}")

            # Cleanup first
            if compress_audio and processed_file != filepath:
                try:
                    os.remove(processed_file)
                except:
                    pass

            if len(chunk_paths) > 1:
                audio_processor.cleanup_temp_files(chunk_paths)

            # Save and store results in session state
            if transcription_text:
                save_success, save_message = file_manager.save_transcription(
                    filepath,
                    transcription_text
                )

                # Store result in session state and trigger result display
                st.session_state.transcription_result = {
                    'success': True,
                    'text': transcription_text,
                    'save_message': save_message,
                    'save_success': save_success
                }
                st.session_state.transcription_completed = True
                st.rerun()
            else:
                # Transcription failed but no exception
                st.session_state.transcription_result = {
                    'success': False,
                    'error': 'Transcription returned empty result'
                }
                st.session_state.transcription_completed = True
                st.rerun()

        except Exception as e:
            import traceback
            # Store error in session state
            st.session_state.transcription_result = {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            st.session_state.transcription_completed = True
            st.rerun()


def page_recordings():
    """Unified recordings page with transcription capability."""
    st.header("📂 Audio Recordings")

    file_manager = st.session_state.file_manager

    # Get all recordings
    recordings = file_manager.list_recordings()

    if not recordings:
        st.info("📭 No recordings found. Record or upload audio in the 'Record & Upload' tab.")
        return

    st.markdown(f"**Total Recordings:** {len(recordings)}")

    # Display recordings in a table-like format
    for filename, filepath, date_str in recordings:
        # Get display name
        display_name = file_manager.get_display_name(filepath)

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 0.5])

            with col1:
                st.markdown(f"**{display_name}**")
                st.caption(f"📅 {date_str} | 📄 {filename}")

            with col2:
                # Check if transcription exists
                if file_manager.has_transcription(filepath):
                    st.success("✓ Transcribed")
                else:
                    st.warning("⚠ Not transcribed")

            with col3:
                # Transcribe button
                if st.button("🎙️", key=f"transcribe_{filename}", use_container_width=True, help="Transcribe"):
                    st.session_state.current_transcribe_file = (filepath, filename)
                    st.session_state.show_transcribe_dialog = True
                    st.rerun()

            with col4:
                # Edit name button
                if st.button("✏️", key=f"edit_{filename}", use_container_width=True, help="Rename"):
                    st.session_state.editing_file = filepath
                    st.session_state.show_rename_dialog = True
                    st.rerun()

            with col5:
                # Delete button
                if st.button("🗑️", key=f"delete_{filename}", use_container_width=True, help="Delete"):
                    success, message = file_manager.delete_recording(filepath)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            # Expandable details
            with st.expander(f"📋 Details: {filename}"):
                # Read and display audio file to avoid Streamlit media storage issues
                try:
                    with open(filepath, 'rb') as audio_file:
                        audio_bytes = audio_file.read()
                        st.audio(audio_bytes, format='audio/wav')
                except Exception as e:
                    st.warning(f"⚠️ Could not load audio file: {str(e)}")

                # Show transcription if exists
                transcription = file_manager.load_transcription(filepath)
                if transcription:
                    st.markdown("**Transcription:**")
                    st.text_area(
                        "Transcription:",
                        value=transcription,
                        height=300,
                        key=f"view_transcription_{filename}",
                        label_visibility="collapsed"
                    )
                else:
                    st.markdown("*No transcription available. Click 'Transcribe' button above.*")

            st.markdown("---")


def page_transcribe():
    """Transcribe page."""
    st.header("🎙️ Transcribe Audio to Text")

    transcription_service = st.session_state.transcription_service
    file_manager = st.session_state.file_manager
    config = st.session_state.config

    # API Configuration
    with st.expander("🔐 API Configuration", expanded=not transcription_service.is_configured()):
        st.markdown("**OpenAI API Key Setup**")
        st.markdown("Your API key is stored securely and never exposed in the UI.")

        api_key_input = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            help="Enter your OpenAI API key (starts with 'sk-')"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💾 Save API Key", use_container_width=True):
                if api_key_input:
                    success, message = transcription_service.set_api_key(api_key_input)
                    if success:
                        if config.save_api_key(api_key_input):
                            st.success(f"✓ {message}\nAPI key saved securely.")
                        else:
                            st.warning(f"✓ {message}\n⚠ Warning: Could not save to file.")
                    else:
                        st.error(f"✗ {message}")
                else:
                    st.error("Please enter an API key.")

        with col2:
            if st.button("📂 Load Saved Key", use_container_width=True):
                api_key = config.load_api_key()
                if api_key:
                    success, message = transcription_service.set_api_key(api_key)
                    if success:
                        st.success("✓ API key loaded successfully.")
                    else:
                        st.error(f"✗ {message}")
                else:
                    st.error("✗ No saved API key found.")

        with col3:
            if st.button("🗑️ Delete Key", use_container_width=True):
                if config.delete_api_key():
                    transcription_service.client = None
                    transcription_service.api_key = None
                    st.success("✓ API key deleted.")
                else:
                    st.error("✗ Error deleting API key.")

    # Transcription Section
    st.markdown("---")
    st.markdown("**Transcribe Audio File**")

    if not transcription_service.is_configured():
        st.warning("⚠️ Please configure your OpenAI API key first.")
        return

    # File selection
    recordings = file_manager.list_recordings()

    if not recordings:
        st.info("No recordings found. Record or upload audio first.")
        return

    file_choices = {f"{filename} ({date})": filepath for filename, filepath, date in recordings}

    selected_file_display = st.selectbox(
        "Select Audio File",
        options=list(file_choices.keys()),
        help="Choose a file from your recordings"
    )

    # Model selection
    st.markdown("**Model Options:**")
    st.markdown("""
    - **GPT-4o Mini Transcribe** ($0.18/hour) - Fast and cost-effective. Best for general use cases.
    - **GPT-4o Transcribe** ($0.36/hour) - High-quality transcription with better accuracy. Ideal for complex audio.
    - **Whisper-1** ($0.36/hour) - OpenAI's original Whisper model. Reliable and well-tested.
    """)

    model_choices = transcription_service.get_model_choices()
    model_labels = [choice[0] for choice in model_choices]
    model_ids = [choice[1] for choice in model_choices]

    selected_model_label = st.selectbox(
        "Transcription Model",
        options=model_labels,
        index=0,
        help="Select the model to use for transcription"
    )

    selected_model_id = model_ids[model_labels.index(selected_model_label)]

    # Language option
    language = st.text_input(
        "Language (Optional)",
        placeholder="e.g., en, ko, ja",
        help="Leave empty for auto-detection"
    )

    # Advanced options
    with st.expander("⚙️ Advanced Options", expanded=False):
        st.markdown("**Audio Processing**")

        compress_audio = st.checkbox(
            "Compress audio before transcription",
            value=True,
            help="Recommended for large files. Reduces file size and API costs."
        )

        # Compression method selection (only show if compression is enabled)
        compression_method = "recommended"
        custom_ffmpeg_options = None

        if compress_audio:
            st.markdown("**Compression Method**")

            # Create options with descriptions
            method_options = {}
            for key, info in COMPRESSION_METHODS.items():
                label = f"{info['name']}"
                method_options[label] = key

            selected_method_label = st.radio(
                "Select compression method:",
                options=list(method_options.keys()),
                index=0,  # Default to first option (recommended)
                help="Choose based on your needs: quality vs speed vs memory usage"
            )
            compression_method = method_options[selected_method_label]

            # Show detailed info about selected method
            method_info = COMPRESSION_METHODS[compression_method]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Est. Compression", method_info['estimated_ratio'])
            with col2:
                st.metric("Speed", method_info['speed'])
            with col3:
                st.metric("Memory", method_info['memory'])

            st.caption(f"ℹ️ {method_info['description']}")

            # Show FFmpeg command options
            st.markdown("**FFmpeg Options**")

            if compression_method == "custom":
                # Allow user to input custom FFmpeg options
                custom_ffmpeg_options = st.text_input(
                    "Custom FFmpeg options:",
                    value=method_info['ffmpeg_options'],
                    help="Specify your own FFmpeg options. Example: -c:a libopus -b:a 32k -ar 16000 -ac 1"
                )
                st.info("💡 The final command will be: `ffmpeg -y -i input.wav [your options] output.opus`")
            else:
                # Display read-only FFmpeg options for preset methods
                st.code(method_info['ffmpeg_options'], language="bash")
                st.caption("📋 These are the FFmpeg options that will be used for compression.")

        chunk_overlap = st.slider(
            "Chunk overlap duration (seconds)",
            min_value=15,
            max_value=120,
            value=60,
            step=15,
            help="Overlap between chunks for long audio files. Higher values preserve more context."
        )

        st.markdown("---")
        st.markdown("**Transcription Features**")

        enable_timestamps = st.checkbox(
            "Enable timestamps",
            value=False,
            help="Add timestamps to transcription (segment-level). Only supported by Whisper-1 model."
        )

        st.info(
            "💡 **Features:**\n"
            "- **Compression**: All methods use FFmpeg for memory-efficient streaming\n"
            "  - *Recommended*: Removes silence, optimized for meetings\n"
            "  - *Fast (MP3)*: Quick compression, standard quality\n"
            "  - *Balanced (Opus)*: Good for speech, efficient\n"
            "  - *Custom*: Specify your own FFmpeg options\n"
            "- **Chunk Overlap**: Preserves context between chunks\n"
            "- **Timestamps**: Adds time markers to transcription (Whisper-1 only)\n\n"
            "**Note:** FFmpeg must be installed on your system for compression.\n"
            "Timestamps and speaker diarization are only available with Whisper-1 model."
        )

    # Transcribe button
    if st.button("🎙️ Transcribe Audio", type="primary", use_container_width=True):
        selected_filepath = file_choices[selected_file_display]
        language_code = language.strip() if language and language.strip() else None

        # Initialize audio processor
        audio_processor = AudioProcessor()

        # Determine transcription format based on timestamp option
        if enable_timestamps:
            response_format = "verbose_json"
            timestamp_granularities = ["segment"]  # Only segment-level, no word-level
        else:
            response_format = "text"
            timestamp_granularities = None

        try:
            # Check audio duration
            duration = audio_processor.get_audio_duration(selected_filepath)
            st.info(f"📊 Audio duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

            # Determine if we need chunking
            needs_chunking = duration > 1400  # 23 minutes 20 seconds

            # Process audio
            processed_file = selected_filepath
            chunk_paths = []

            # Step 1: Compression (if enabled)
            if compress_audio:
                st.markdown("### 📦 Step 1: Compressing Audio")
                progress_placeholder = st.empty()
                status_placeholder = st.empty()

                def compression_progress(message):
                    status_placeholder.text(message)

                # Get file extension based on compression method
                method_info = COMPRESSION_METHODS[compression_method]
                file_extension = method_info['extension']

                compressed_path = os.path.join(
                    tempfile.gettempdir(),
                    f"compressed_{os.path.splitext(os.path.basename(selected_filepath))[0]}{file_extension}"
                )

                success, output_path, message = audio_processor.compress_audio(
                    selected_filepath,
                    compressed_path,
                    method=compression_method,
                    custom_ffmpeg_options=custom_ffmpeg_options,
                    progress_callback=compression_progress
                )

                if success:
                    st.success(message)
                    processed_file = output_path
                else:
                    st.error(message)
                    st.stop()

            # Step 2: Chunking (if needed)
            if needs_chunking:
                st.markdown("### ✂️ Step 2: Splitting into Overlapping Chunks")
                st.info(f"🔪 Audio is too long ({duration:.0f}s > 1400s). Splitting into chunks with {chunk_overlap}-second overlaps...")

                chunk_progress = st.progress(0)
                chunk_status = st.empty()

                def chunking_progress(current, total, message):
                    chunk_status.text(message)
                    chunk_progress.progress(current / total)

                chunk_paths = audio_processor.split_audio_with_overlap(
                    processed_file,
                    chunk_duration=1200,  # 20 minutes
                    overlap_duration=chunk_overlap,
                    progress_callback=chunking_progress
                )

                st.success(f"✅ Split into {len(chunk_paths)} chunks")
            else:
                chunk_paths = [processed_file]

            # Step 3: Transcription
            st.markdown("### 🎙️ Step 3: Transcribing Audio")

            if len(chunk_paths) > 1:
                st.info(f"📝 Processing {len(chunk_paths)} chunks in parallel...")

                trans_progress = st.progress(0)
                trans_status = st.empty()

                def transcription_progress(current, total, message):
                    trans_status.text(message)
                    trans_progress.progress(current / total)

                # Batch transcription
                transcriptions, errors = transcription_service.transcribe_chunks_batch(
                    chunk_paths,
                    selected_model_id,
                    language_code,
                    timestamp_granularities,
                    response_format,
                    progress_callback=transcription_progress
                )

                if errors:
                    st.warning(f"⚠️ Some chunks had errors:\n" + "\n".join(errors))

                # Filter out None values
                valid_transcriptions = [t for t in transcriptions if t is not None]

                if valid_transcriptions:
                    # Merge transcriptions
                    transcription_text = audio_processor.merge_transcriptions(valid_transcriptions)
                    st.success(f"✅ Successfully transcribed {len(valid_transcriptions)}/{len(chunk_paths)} chunks")
                else:
                    st.error("❌ All chunks failed to transcribe")
                    transcription_text = None

            else:
                # Single file transcription
                with st.spinner("Transcribing..."):
                    transcription_text, status_message = transcription_service.transcribe_audio(
                        chunk_paths[0],
                        selected_model_id,
                        language_code,
                        timestamp_granularities,
                        response_format
                    )

                if transcription_text:
                    st.success(f"✓ {status_message}")
                else:
                    st.error(f"✗ {status_message}")

            # Save and display results
            if transcription_text:
                # Save transcription
                save_success, save_message = file_manager.save_transcription(
                    selected_filepath,
                    transcription_text
                )

                if save_success:
                    st.info(save_message)
                else:
                    st.warning(f"⚠ {save_message}")

                st.markdown("### 📄 Transcription Result")
                st.text_area(
                    "Transcription:",
                    value=transcription_text,
                    height=400,
                    label_visibility="collapsed"
                )

            # Cleanup
            if compress_audio and processed_file != selected_filepath:
                try:
                    os.remove(processed_file)
                except:
                    pass

            if len(chunk_paths) > 1:
                audio_processor.cleanup_temp_files(chunk_paths)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def page_browse_recordings():
    """Browse Recordings page."""
    st.header("📂 Browse and Manage Audio Files")

    file_manager = st.session_state.file_manager

    # Refresh button
    if st.button("🔄 Refresh List", use_container_width=True):
        st.rerun()

    recordings = file_manager.list_recordings()

    if not recordings:
        st.info("No recordings found. Record or upload audio first.")
        return

    # File selection
    file_choices = {f"{filename} ({date})": (filepath, filename) for filename, filepath, date in recordings}

    selected_file_display = st.selectbox(
        "Select Recording",
        options=list(file_choices.keys()),
        help="Select a file to view details and play"
    )

    if selected_file_display:
        filepath, filename = file_choices[selected_file_display]

        # File information
        file_info = file_manager.get_file_info(filepath)
        st.info(file_info)

        # Audio player
        st.audio(filepath)

        # Transcription display
        transcription = file_manager.load_transcription(filepath)
        if transcription:
            st.markdown("**Transcription:**")
            st.text_area(
                "Transcription:",
                value=transcription,
                height=400,
                key=f"browse_transcription_{filename}",
                label_visibility="collapsed"
            )
        else:
            st.markdown("*No transcription available for this file.*")

        # Delete button
        st.markdown("---")
        if st.button("🗑️ Delete Selected File", type="secondary", use_container_width=True):
            success, message = file_manager.delete_recording(filepath)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def create_streamlit_app(
    recorder: AudioRecorder,
    file_manager: AudioFileManager,
    transcription_service: TranscriptionService,
    config: SecureConfig
):
    """Create and run Streamlit app."""

    # Page config
    st.set_page_config(
        page_title="AI Meeting Notes",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state(recorder, file_manager, transcription_service, config)

    # Sidebar navigation
    st.sidebar.title("🎙️ AI Meeting Notes")
    st.sidebar.markdown("Record or upload audio to transcribe your meetings.")

    # API Key Settings button in sidebar
    if st.sidebar.button("⚙️ API Key Settings", use_container_width=True):
        st.session_state.show_api_dialog = True

    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["Record & Upload", "Recordings"],
        label_visibility="collapsed"
    )

    # Clear recording preview when switching pages
    if 'current_page' not in st.session_state:
        st.session_state.current_page = page
    elif st.session_state.current_page != page:
        # Page changed, clear preview
        st.session_state.show_last_recording = False
        st.session_state.last_recorded_file = None
        st.session_state.current_page = page

    # Route to appropriate page
    if page == "Record & Upload":
        page_record_and_upload()
    elif page == "Recordings":
        page_recordings()

    # Show dialogs if triggered (must be after page rendering)
    if st.session_state.get('show_api_dialog', False):
        show_api_key_dialog()

    if st.session_state.get('show_rename_dialog', False):
        if 'editing_file' in st.session_state:
            filepath = st.session_state.editing_file
            show_rename_dialog(filepath)

    if st.session_state.get('show_transcribe_dialog', False):
        if 'current_transcribe_file' in st.session_state:
            filepath, filename = st.session_state.current_transcribe_file
            show_transcribe_dialog(filepath, filename)
