"""Gradio web UI for AI Meeting Notes."""

import gradio as gr
from src.audio import AudioRecorder
from src.file_manager import AudioFileManager
from src.transcription import TranscriptionService
from src.config import SecureConfig


def create_ui(
    recorder: AudioRecorder,
    file_manager: AudioFileManager,
    transcription_service: TranscriptionService,
    config: SecureConfig
) -> gr.Blocks:
    """Create Gradio web UI for AI Meeting Notes."""

    with gr.Blocks(title="AI Meeting Notes") as app:
        gr.Markdown("# AI Meeting Notes")
        gr.Markdown("Record or upload audio to transcribe your meetings.")

        # Store recorder state and file list refresh trigger
        recording_state = gr.State(False)
        refresh_trigger = gr.State(0)

        with gr.Tab("Record & Upload"):
            gr.Markdown("### Record or Upload Audio")

            with gr.Accordion("Direct Recording", open=True):
                gr.Markdown("Select your microphone and click 'Start Recording' to begin.")

                # Microphone selection
                default_mic = recorder.get_default_microphone()
                mic_dropdown = gr.Dropdown(
                    choices=recorder.get_microphone_devices(),
                    value=default_mic,
                    label="Select Microphone",
                    info="Choose the microphone device to use for recording"
                )

                # Sample rate selection
                sample_rate_radio = gr.Radio(
                    choices=[16000, 44100, 48000],
                    value=16000,
                    label="Sample Rate (Hz)",
                    info="Higher sample rate = better quality but larger file size"
                )

                # Recording controls
                with gr.Row():
                    start_btn = gr.Button("Start Recording", variant="primary", size="lg")
                    stop_btn = gr.Button("Stop Recording", variant="stop", size="lg", interactive=False)

                # Status and output
                record_status = gr.Textbox(label="Status", value="Ready to record", lines=2)
                recorded_audio = gr.Audio(label="Recorded Audio", type="filepath", visible=False)

            with gr.Accordion("Upload Audio File", open=True):
                gr.Markdown("Upload an existing audio file to your recordings.")
                upload_input = gr.Audio(
                    sources=["upload"],
                    type="filepath",
                    label="Upload Audio File"
                )
                upload_btn = gr.Button("Save Upload", variant="primary")
                upload_output = gr.Textbox(label="Status", lines=2)

            def on_start_recording(device_idx, sample_rate):
                """Handle start recording button click."""
                success, message = recorder.start_recording(device_idx, sample_rate)
                if success:
                    return (
                        gr.update(interactive=False),  # start_btn
                        gr.update(interactive=True),   # stop_btn
                        message,                        # status
                        gr.update(visible=False),      # recorded_audio
                        True                            # recording_state
                    )
                else:
                    return (
                        gr.update(interactive=True),
                        gr.update(interactive=False),
                        message,
                        gr.update(visible=False),
                        False
                    )

            def on_stop_recording():
                """Handle stop recording button click."""
                audio_file, message = recorder.stop_recording()
                if audio_file:
                    message += "\n→ Go to Browse Recordings tab to view your file."
                return (
                    gr.update(interactive=True),   # start_btn
                    gr.update(interactive=False),  # stop_btn
                    message,                        # status
                    gr.update(value=audio_file, visible=True) if audio_file else gr.update(visible=False),  # recorded_audio
                    False                           # recording_state
                )

            def on_upload(audio_file):
                """Handle file upload save."""
                if audio_file is None:
                    return "No file selected."
                filepath, message = file_manager.save_uploaded_file(audio_file)
                if filepath:
                    message += "\n→ Go to Browse Recordings tab to view your file."
                return message

            start_btn.click(
                fn=on_start_recording,
                inputs=[mic_dropdown, sample_rate_radio],
                outputs=[start_btn, stop_btn, record_status, recorded_audio, recording_state]
            )

            stop_btn.click(
                fn=on_stop_recording,
                outputs=[start_btn, stop_btn, record_status, recorded_audio, recording_state]
            )

            upload_btn.click(
                fn=on_upload,
                inputs=upload_input,
                outputs=upload_output
            )

        with gr.Tab("Transcribe"):
            gr.Markdown("### Transcribe Audio to Text")
            gr.Markdown("Configure OpenAI API and transcribe your audio files.")

            # API Key Configuration Section
            with gr.Accordion("API Configuration", open=True):
                gr.Markdown("**OpenAI API Key Setup**")
                gr.Markdown("Your API key is stored securely and never exposed in the UI.")

                api_key_input = gr.Textbox(
                    label="OpenAI API Key",
                    placeholder="sk-...",
                    type="password",
                    info="Enter your OpenAI API key (starts with 'sk-')"
                )

                with gr.Row():
                    save_key_btn = gr.Button("Save API Key", variant="primary")
                    load_key_btn = gr.Button("Load Saved Key", variant="secondary")
                    delete_key_btn = gr.Button("Delete Key", variant="stop")

                api_key_status = gr.Textbox(label="Status", lines=2, interactive=False)

                def on_save_api_key(api_key):
                    """Handle saving API key."""
                    success, message = transcription_service.set_api_key(api_key)
                    if success:
                        if config.save_api_key(api_key):
                            return f"✓ {message}\nAPI key saved securely.", ""
                        else:
                            return f"✓ {message}\n⚠ Warning: Could not save to file.", ""
                    return f"✗ {message}", api_key

                def on_load_api_key():
                    """Handle loading saved API key."""
                    api_key = config.load_api_key()
                    if api_key:
                        success, message = transcription_service.set_api_key(api_key)
                        if success:
                            return f"✓ API key loaded successfully.", ""
                        return f"✗ {message}", ""
                    return "✗ No saved API key found.", ""

                def on_delete_api_key():
                    """Handle deleting API key."""
                    if config.delete_api_key():
                        transcription_service.client = None
                        transcription_service.api_key = None
                        return "✓ API key deleted.", ""
                    return "✗ Error deleting API key.", ""

                save_key_btn.click(
                    fn=on_save_api_key,
                    inputs=api_key_input,
                    outputs=[api_key_status, api_key_input]
                )

                load_key_btn.click(
                    fn=on_load_api_key,
                    outputs=[api_key_status, api_key_input]
                )

                delete_key_btn.click(
                    fn=on_delete_api_key,
                    outputs=[api_key_status, api_key_input]
                )

            # Transcription Section
            gr.Markdown("---")
            gr.Markdown("**Transcribe Audio File**")

            # File selection
            transcribe_file_dropdown = gr.Dropdown(
                label="Select Audio File",
                choices=[],
                interactive=True,
                info="Choose a file from your recordings"
            )

            refresh_transcribe_files_btn = gr.Button("Refresh File List", variant="secondary")

            # Model selection with detailed info
            model_info_md = """
**Model Options:**

- **GPT-4o Mini Transcribe** ($0.18/hour) - Fast and cost-effective. Best for general use cases.
- **GPT-4o Transcribe** ($0.36/hour) - High-quality transcription with better accuracy. Ideal for complex audio.
- **Whisper-1** ($0.36/hour) - OpenAI's original Whisper model. Reliable and well-tested.
"""
            gr.Markdown(model_info_md)

            model_choices = transcription_service.get_model_choices()
            model_dropdown = gr.Dropdown(
                label="Transcription Model",
                choices=[choice[0] for choice in model_choices],
                value=model_choices[0][0],  # Default to first choice
                interactive=True
            )

            # Language option
            language_input = gr.Textbox(
                label="Language (Optional)",
                placeholder="e.g., en, ko, ja",
                info="Leave empty for auto-detection"
            )

            # Transcribe button
            transcribe_btn = gr.Button("Transcribe Audio", variant="primary", size="lg")

            # Results
            transcription_output = gr.Textbox(
                label="Transcription Result",
                lines=10,
                interactive=True,
                info="Transcribed text will appear here"
            )

            transcription_status = gr.Textbox(label="Status", lines=2, interactive=False)

            def refresh_transcribe_file_list():
                """Refresh the file list for transcription."""
                recordings = file_manager.list_recordings()
                if not recordings:
                    return gr.update(choices=[], value=None)

                choices = [f"{filename} ({date})" for filename, _, date in recordings]
                return gr.update(choices=choices, value=None)

            def on_transcribe(selected_file, selected_model, language):
                """Handle transcription request."""
                if not transcription_service.is_configured():
                    return "", "✗ Please configure your OpenAI API key first."

                if not selected_file:
                    return "", "✗ Please select an audio file."

                # Extract filename and find file path
                filename = selected_file.split(" (")[0]
                recordings = file_manager.list_recordings()

                file_path = None
                for fname, fpath, _ in recordings:
                    if fname == filename:
                        file_path = fpath
                        break

                if not file_path:
                    return "", "✗ File not found."

                # Extract model ID from selection
                model_id = None
                for label, mid in model_choices:
                    if label == selected_model:
                        model_id = mid
                        break

                if not model_id:
                    model_id = "gpt-4o-mini-transcribe"

                # Perform transcription
                language_code = language.strip() if language and language.strip() else None
                transcription_text, status_message = transcription_service.transcribe_audio(
                    file_path, model_id, language_code
                )

                if transcription_text:
                    # Save transcription
                    save_success, save_message = file_manager.save_transcription(file_path, transcription_text)
                    if save_success:
                        return transcription_text, f"✓ {status_message}\n{save_message}"
                    else:
                        return transcription_text, f"✓ {status_message}\n⚠ {save_message}"
                else:
                    return "", f"✗ {status_message}"

            refresh_transcribe_files_btn.click(
                fn=refresh_transcribe_file_list,
                outputs=transcribe_file_dropdown
            )

            transcribe_btn.click(
                fn=on_transcribe,
                inputs=[transcribe_file_dropdown, model_dropdown, language_input],
                outputs=[transcription_output, transcription_status]
            )

            # Auto-load file list on tab load
            app.load(
                fn=refresh_transcribe_file_list,
                outputs=transcribe_file_dropdown
            )

        with gr.Tab("Browse Recordings"):
            gr.Markdown("### Browse and Manage Audio Files")
            gr.Markdown("View all recordings and uploaded files.")

            refresh_btn = gr.Button("Refresh List", variant="secondary")

            with gr.Row():
                with gr.Column(scale=2):
                    file_list = gr.Dropdown(
                        label="Recordings",
                        choices=[],
                        interactive=True,
                        info="Select a file to view details and play"
                    )

                with gr.Column(scale=1):
                    delete_btn = gr.Button("Delete Selected", variant="stop")

            file_info = gr.Textbox(label="File Information", lines=3)
            audio_player = gr.Audio(label="Audio Player", type="filepath", visible=False)

            transcription_display = gr.Textbox(
                label="Transcription",
                lines=10,
                interactive=False,
                visible=False,
                info="Transcription text for this audio file"
            )

            with gr.Row():
                copy_btn = gr.Button("Copy Transcription", variant="secondary", visible=False)

            def refresh_file_list():
                """Refresh the list of recordings."""
                recordings = file_manager.list_recordings()
                if not recordings:
                    return (
                        gr.update(choices=[], value=None),
                        "No recordings found.",
                        gr.update(visible=False),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False)
                    )

                choices = [f"{filename} ({date})" for filename, _, date in recordings]
                return (
                    gr.update(choices=choices, value=None),
                    "",
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False)
                )

            def on_file_select(selected):
                """Handle file selection."""
                if not selected:
                    return (
                        "No file selected.",
                        gr.update(visible=False),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False)
                    )

                # Extract filename from selection (remove date part)
                filename = selected.split(" (")[0]

                # Find the full path
                recordings = file_manager.list_recordings()
                for fname, fpath, _ in recordings:
                    if fname == filename:
                        info = file_manager.get_file_info(fpath)

                        # Load transcription if available
                        transcription = file_manager.load_transcription(fpath)

                        if transcription:
                            return (
                                info,
                                gr.update(value=fpath, visible=True),
                                gr.update(value=transcription, visible=True),
                                gr.update(visible=True)
                            )
                        else:
                            return (
                                info,
                                gr.update(value=fpath, visible=True),
                                gr.update(visible=False, value=""),
                                gr.update(visible=False)
                            )

                return (
                    "File not found.",
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False)
                )

            def on_delete(selected):
                """Handle file deletion."""
                if not selected:
                    return (
                        "No file selected.",
                        gr.update(choices=[], value=None),
                        gr.update(visible=False),
                        gr.update(visible=False, value=""),
                        gr.update(visible=False)
                    )

                # Extract filename from selection
                filename = selected.split(" (")[0]

                # Find and delete the file
                recordings = file_manager.list_recordings()
                for fname, fpath, _ in recordings:
                    if fname == filename:
                        success, message = file_manager.delete_recording(fpath)

                        # Refresh the list
                        new_recordings = file_manager.list_recordings()
                        choices = [f"{fn} ({dt})" for fn, _, dt in new_recordings]

                        return (
                            message,
                            gr.update(choices=choices, value=None),
                            gr.update(visible=False),
                            gr.update(visible=False, value=""),
                            gr.update(visible=False)
                        )

                return (
                    "File not found.",
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=False, value=""),
                    gr.update(visible=False)
                )

            # Event handlers
            refresh_btn.click(
                fn=refresh_file_list,
                outputs=[file_list, file_info, audio_player, transcription_display, copy_btn]
            )

            file_list.change(
                fn=on_file_select,
                inputs=file_list,
                outputs=[file_info, audio_player, transcription_display, copy_btn]
            )

            delete_btn.click(
                fn=on_delete,
                inputs=file_list,
                outputs=[file_info, file_list, audio_player, transcription_display, copy_btn]
            )

            # Copy button functionality (uses JS to copy to clipboard)
            copy_btn.click(
                fn=lambda x: x,
                inputs=transcription_display,
                outputs=None,
                js="(text) => {navigator.clipboard.writeText(text); return text;}"
            )

            # Load initial file list
            app.load(
                fn=refresh_file_list,
                outputs=[file_list, file_info, audio_player, transcription_display, copy_btn]
            )

    return app
