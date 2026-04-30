"""Semantic enums for the LLm stress tester."""

from enum import StrEnum


class RateUnit(StrEnum):
    """Rate measurement unit."""

    RPS = "rps"
    RPM = "rpm"


class BenchmarkSuite(StrEnum):
    """Supported benchmark suite categories."""

    CODING = "coding"
    MATH = "math"
    KNOWLEDGE = "knowledge"
    INSTRUCTION_FOLLOWING = "instruction_following"
    MULTI_TURN = "multi_turn"
    LONG_CONTEXT = "long_context"
    TEXT_PROCESSING = "text_processing"


class RequestStatus(StrEnum):
    """Result status of a single request."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"


class RunStatus(StrEnum):
    """Overall test run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
