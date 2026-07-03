import logging
import sys

def get_logger(name: str = "expense-audit-bot"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

class TraceLogger:
    def __init__(self, logger, trace_id: str):
        self.logger = logger
        self.trace_id = trace_id
        
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, extra={"trace_id": self.trace_id}, *args, **kwargs)
        
    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, extra={"trace_id": self.trace_id}, *args, **kwargs)
        
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, extra={"trace_id": self.trace_id}, *args, **kwargs)
