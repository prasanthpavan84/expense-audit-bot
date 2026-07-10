import datetime
import json
import logging
import os
import sys
from contextvars import ContextVar

# ContextVar to track the request correlation ID across threads/coroutines
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    """Filter that injects the current ContextVar trace_id into the log record."""

    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True


class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured logs in JSON format."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        # In case extra keys are passed (like agent, state, latency, workflow)
        for key in ["agent", "state", "latency", "workflow"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str = "expense-audit-bot"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Check if structured JSON logging is enabled via environment
    import os

    use_json = os.getenv("STRUCTURED_LOGGING", "false").lower() in ("true", "1", "yes")

    # Add handler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Add trace ID filter to handler
        handler.addFilter(TraceIdFilter())

        if use_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s")

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class TraceLogger:
    """Backward compatibility wrapper."""

    def __init__(self, logger, trace_id: str):
        self.logger = logger
        self.trace_id = trace_id

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, extra={"trace_id": self.trace_id}, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, extra={"trace_id": self.trace_id}, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, extra={"trace_id": self.trace_id}, *args, **kwargs)


def log_pipeline_stage(
    session_id: str,
    audit_id: str,
    stage: str,
    duration: float,
    decision: str,
    confidence: float,
    errors: list[str],
    warning_count: int,
) -> None:
    """Logs a structured JSON message for a completed pipeline stage/agent."""
    logger = get_logger("pipeline_stage")
    log_data = {
        "event_type": "pipeline_stage_completed",
        "session_id": session_id,
        "audit_id": audit_id,
        "stage": stage,
        "duration_ms": int(duration * 1000),
        "decision": decision,
        "confidence": confidence,
        "errors": errors,
        "warning_count": warning_count,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }

    use_json = os.getenv("STRUCTURED_LOGGING", "false").lower() in ("true", "1", "yes")
    if use_json:
        logger.info(json.dumps(log_data))
    else:
        logger.info(
            f"Stage '{stage}' completed for session={session_id}, audit={audit_id} in {duration:.3f}s. "
            f"Decision={decision}, Confidence={confidence:.2f}, Errors={errors}, Warnings={warning_count}"
        )
