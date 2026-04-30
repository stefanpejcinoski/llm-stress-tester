"""Semantic constants for the LLm stress tester."""

# Rate slider range - always displayed as integers, converted internally
MIN_RATE_SLIDER_VALUE: int = 1
MAX_RATE_SLIDER_VALUE: int = 2000

# Default upstream API path for OpenAI-compatible endpoints
DEFAULT_API_PATH: str = "v1/chat/completions"

# HTTP settings
DEFAULT_TIMEOUT: float = 60.0  # seconds per request
MAX_CONCURRENT_CONNECTIONS: int = 100
