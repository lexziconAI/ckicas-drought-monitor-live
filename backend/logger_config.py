import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

# Redaction patterns for security
SENSITIVE_KEYS = ["api_key", "authorization", "password", "secret"]

class SecurityFormatter(logging.Formatter):
    """JSON formatter that automatically redacts sensitive data."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        
        # Merge extra fields if they exist
        if hasattr(record, "props"):
            log_obj.update(record.props) # type: ignore

        # Redact sensitive info in message or props
        return json.dumps(self._redact(log_obj))

    def _redact(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: ("***REDACTED***" if k.lower() in SENSITIVE_KEYS else self._redact(v)) 
                    for k, v in data.items()}
        elif isinstance(data, list):
            return [self._redact(i) for i in data]
        elif isinstance(data, str):
            # Basic string scan for key-like patterns (simplified)
            if "sk-" in data: 
                return data.replace(data[data.find("sk-"):data.find("sk-")+10], "sk-***")
            return data
        return data

def get_logger(name: str, level: str = "DEBUG") -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Clear existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SecurityFormatter())
    logger.addHandler(handler)
    
    logger.setLevel(getattr(logging, level.upper()))
    return logger

# Global instance
logger = get_logger("SATYA_SECURE", "DEBUG")
