import logging
import sys
import json
import datetime
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
            "trace_id": getattr(record, "trace_id", "-")
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
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s')
            
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
