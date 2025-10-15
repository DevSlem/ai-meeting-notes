"""
Meeting Notes Service
Converts transcription text to structured meeting notes using OpenAI GPT-5 models.
"""

from pathlib import Path
from typing import Literal, Optional
from openai import OpenAI


# GPT-5 series models configuration
MEETING_NOTES_MODELS = {
    "gpt-5": {
        "name": "GPT-5",
        "model_id": "gpt-5",
        "description": "Highest quality reasoning model, best for complex meetings",
        "pricing": {"input": 1.25, "output": 10.0},  # per 1M tokens
        "supports_reasoning_effort": True,
    },
    "gpt-5-mini": {
        "name": "GPT-5 Mini",
        "model_id": "gpt-5-mini",
        "description": "Balanced performance and cost, suitable for most meetings",
        "pricing": {"input": 0.25, "output": 2.0},  # per 1M tokens
        "supports_reasoning_effort": True,
    },
    "gpt-5-nano": {
        "name": "GPT-5 Nano",
        "model_id": "gpt-5-nano",
        "description": "Fastest and most affordable, great for simple summaries",
        "pricing": {"input": 0.05, "output": 0.40},  # per 1M tokens
        "supports_reasoning_effort": True,
    },
}

ModelType = Literal["gpt-5", "gpt-5-mini", "gpt-5-nano"]
ReasoningEffort = Literal["minimal", "low", "medium", "high"]


class MeetingNotesService:
    """Service for converting transcription text to meeting notes using OpenAI API."""

    def __init__(self, api_key: str, prompts_dir: str = "prompts/meeting-notes"):
        """
        Initialize the meeting notes service.

        Args:
            api_key: OpenAI API key
            prompts_dir: Directory containing prompt templates
        """
        self.client = OpenAI(api_key=api_key)
        self.prompts_dir = Path(prompts_dir)

    def load_prompt(self, prompt_name: str = "default", language: Optional[str] = None) -> str:
        """
        Load a prompt template from the prompts directory.

        Args:
            prompt_name: Name of the prompt file (without .txt extension)
            language: Target language for the meeting notes (e.g., "English", "Korean", "Japanese")
                     If None, auto-detect from transcription

        Returns:
            The prompt text content with language instruction applied

        Raises:
            FileNotFoundError: If the prompt file doesn't exist
        """
        prompt_path = self.prompts_dir / f"{prompt_name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                f"Please create it or use 'default' prompt."
            )
        prompt_text = prompt_path.read_text(encoding="utf-8")

        # Replace language instruction placeholder
        if language:
            language_instruction = f"Write the meeting notes in {language}"
        else:
            language_instruction = "Auto-detect the language of the transcription and respond in the SAME language"

        prompt_text = prompt_text.replace("{LANGUAGE_INSTRUCTION}", language_instruction)

        return prompt_text

    def generate_meeting_notes(
        self,
        transcription_text: str,
        model: ModelType = "gpt-5",
        system_prompt: Optional[str] = None,
        prompt_name: str = "default",
        language: Optional[str] = None,
        reasoning_effort: ReasoningEffort = "medium",
        max_completion_tokens: int = 4000,
    ) -> dict:
        """
        Convert transcription text to structured meeting notes.

        Args:
            transcription_text: The raw transcription text to convert
            model: GPT-5 model to use (gpt-5, gpt-5-mini, or gpt-5-nano)
            system_prompt: Custom system prompt (if provided, ignores prompt_name and language)
            prompt_name: Name of the prompt template to use (default: "default")
            language: Target language for the meeting notes (e.g., "English", "Korean", "Japanese")
                     If None, auto-detect from transcription
            reasoning_effort: Reasoning effort level for GPT-5 models
            max_completion_tokens: Maximum tokens in the response (GPT-5 uses this instead of max_tokens)

        Note:
            GPT-5 models do not support custom temperature values - only default (1.0) is supported.

        Returns:
            Dictionary containing:
                - meeting_notes: Generated meeting notes text
                - model_used: Model ID that was used
                - usage: Token usage information
                - reasoning_tokens: Number of reasoning tokens used (if applicable)

        Raises:
            ValueError: If invalid model or parameters provided
            openai.OpenAIError: If API call fails
        """
        # Validate model
        if model not in MEETING_NOTES_MODELS:
            raise ValueError(
                f"Invalid model: {model}. Must be one of: {list(MEETING_NOTES_MODELS.keys())}"
            )

        # Validate reasoning_effort
        valid_efforts = ["minimal", "low", "medium", "high"]
        if reasoning_effort not in valid_efforts:
            raise ValueError(
                f"Invalid reasoning_effort: {reasoning_effort}. Must be one of: {valid_efforts}"
            )

        # Load system prompt if not provided
        if system_prompt is None:
            system_prompt = self.load_prompt(prompt_name, language)

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcription_text},
        ]

        # Call OpenAI API with GPT-5 specific parameters
        # Note: GPT-5 models only support default temperature (1.0)
        response = self.client.chat.completions.create(
            model=MEETING_NOTES_MODELS[model]["model_id"],
            messages=messages,
            reasoning_effort=reasoning_effort,
            max_completion_tokens=max_completion_tokens,
        )

        # Extract response data
        meeting_notes = response.choices[0].message.content
        usage = response.usage

        # Build result dictionary
        result = {
            "meeting_notes": meeting_notes,
            "model_used": model,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
        }

        # Add reasoning tokens if present (GPT-5 models)
        if hasattr(usage, "completion_tokens_details"):
            details = usage.completion_tokens_details
            if hasattr(details, "reasoning_tokens") and details.reasoning_tokens:
                result["usage"]["reasoning_tokens"] = details.reasoning_tokens

        return result

    def estimate_cost(
        self,
        transcription_text: str,
        model: ModelType = "gpt-5",
        estimated_output_tokens: int = 2000,
    ) -> dict:
        """
        Estimate the cost of generating meeting notes.

        Args:
            transcription_text: The transcription text to process
            model: Model to use for estimation
            estimated_output_tokens: Estimated number of output tokens

        Returns:
            Dictionary with cost estimation:
                - input_tokens: Estimated input tokens
                - output_tokens: Estimated output tokens
                - input_cost: Cost for input in USD
                - output_cost: Cost for output in USD
                - total_cost: Total estimated cost in USD
        """
        # Rough estimation: 1 token ≈ 4 characters for English, less for other languages
        estimated_input_tokens = len(transcription_text) // 4

        pricing = MEETING_NOTES_MODELS[model]["pricing"]

        input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "input_tokens": estimated_input_tokens,
            "output_tokens": estimated_output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "model": model,
        }

    def get_available_prompts(self) -> list[str]:
        """
        Get list of available prompt templates.

        Returns:
            List of prompt names (without .txt extension)
        """
        if not self.prompts_dir.exists():
            return []

        return [
            p.stem for p in self.prompts_dir.glob("*.txt") if p.is_file()
        ]
