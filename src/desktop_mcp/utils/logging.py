"""
Enhanced Logging for Desktop MCP

Provides comprehensive logging capabilities with file rotation,
multiple handlers, and configurable formatting.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def setup_logging(config: Dict[str, Any]):
    """
    Setup logging based on configuration
    
    Args:
        config: Logging configuration dictionary
    """
    # Default logging config
    default_config = {
        "level": "INFO",
        "file": "data/logs/desktop_mcp.log",
        "max_size": "10MB",
        "backup_count": 5,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "console_enabled": True,
        "file_enabled": True
    }
    
    # Merge with provided config
    config = {**default_config, **config}
    
    # Parse log level
    level = getattr(logging, config["level"].upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(config["format"])
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if config["console_enabled"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if config["file_enabled"]:
        log_file = Path(config["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Parse max size
        max_bytes = parse_size(config["max_size"])
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=config["backup_count"]
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Add error handler for critical errors
    error_handler = ErrorFileHandler()
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    logging.info("Logging system initialized")


def parse_size(size_str: str) -> int:
    """
    Parse size string to bytes
    
    Args:
        size_str: Size string like "10MB", "1GB", etc.
        
    Returns:
        Size in bytes
    """
    size_str = size_str.upper().strip()
    
    # Extract number and unit
    import re
    match = re.match(r'(\d+(?:\.\d+)?)\s*([KMGT]?B?)', size_str)
    
    if not match:
        return 10 * 1024 * 1024  # Default 10MB
    
    number = float(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024,
        '': 1  # No unit = bytes
    }
    
    return int(number * multipliers.get(unit, 1))


class ErrorFileHandler(logging.Handler):
    """
    Special handler for error logs that creates separate error files
    """
    
    def __init__(self):
        super().__init__()
        self.error_dir = Path("data/logs/errors")
        self.error_dir.mkdir(parents=True, exist_ok=True)
    
    def emit(self, record):
        """
        Emit an error record to a dated error file
        
        Args:
            record: Log record
        """
        if record.levelno >= logging.ERROR:
            try:
                # Create error file with date
                date_str = datetime.now().strftime("%Y-%m-%d")
                error_file = self.error_dir / f"errors_{date_str}.log"
                
                # Format the record
                message = self.format(record)
                
                # Write to error file
                with open(error_file, 'a', encoding='utf-8') as f:
                    f.write(message + '\n')
                    
                    # Add stack trace if available
                    if record.exc_info:
                        import traceback
                        f.write(traceback.format_exception(*record.exc_info)[0])
                        f.write('\n')
                
            except Exception:
                # Don't let logging errors crash the application
                pass


class PerformanceLogger:
    """
    Performance logging utility for timing operations
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Performance.{name}")
        self.start_time = None
    
    def start(self):
        """Start timing"""
        self.start_time = datetime.now()
        self.logger.debug(f"Started: {self.name}")
    
    def stop(self, message: Optional[str] = None):
        """
        Stop timing and log duration
        
        Args:
            message: Optional message to include
        """
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            log_msg = f"Completed: {self.name} in {duration:.3f}s"
            
            if message:
                log_msg += f" - {message}"
            
            self.logger.info(log_msg)
            self.start_time = None
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type:
            self.logger.error(f"Failed: {self.name} - {exc_val}")
        else:
            self.stop()


class StructuredLogger:
    """
    Structured logging utility for better log analysis
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_event(self, event: str, level: str = "INFO", **kwargs):
        """
        Log a structured event
        
        Args:
            event: Event name/type
            level: Log level
            **kwargs: Additional event data
        """
        level_num = getattr(logging, level.upper(), logging.INFO)
        
        # Create structured message
        event_data = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        # Log as JSON-like structure
        message = f"EVENT:{event}"
        for key, value in kwargs.items():
            message += f" {key}={value}"
        
        self.logger.log(level_num, message)
    
    def log_command_execution(self, command: str, success: bool, duration: float, **kwargs):
        """Log command execution event"""
        self.log_event(
            "command_execution",
            level="INFO" if success else "WARNING",
            command=command,
            success=success,
            duration=duration,
            **kwargs
        )
    
    def log_tool_execution(self, tool_name: str, success: bool, duration: float, **kwargs):
        """Log tool execution event"""
        self.log_event(
            "tool_execution",
            level="INFO" if success else "ERROR",
            tool_name=tool_name,
            success=success,
            duration=duration,
            **kwargs
        )
    
    def log_system_event(self, event_type: str, **kwargs):
        """Log system event"""
        self.log_event(
            "system_event",
            level="INFO",
            event_type=event_type,
            **kwargs
        )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    """
    Get a performance logger
    
    Args:
        name: Operation name
        
    Returns:
        PerformanceLogger instance
    """
    return PerformanceLogger(name)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


def log_startup_info():
    """Log system startup information"""
    logger = get_structured_logger("desktop_mcp.startup")
    
    import platform
    import sys
    
    logger.log_system_event(
        "startup",
        python_version=sys.version,
        platform=platform.platform(),
        architecture=platform.architecture()[0],
        processor=platform.processor(),
        memory_info=get_memory_info()
    )


def get_memory_info() -> Dict[str, Any]:
    """
    Get memory information
    
    Returns:
        Dictionary with memory info
    """
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent_used": memory.percent
        }
    except ImportError:
        return {"error": "psutil not available"}


def configure_third_party_loggers():
    """Configure third-party library loggers to reduce noise"""
    # Reduce noise from common libraries
    noisy_loggers = [
        "urllib3.connectionpool",
        "selenium.webdriver.remote.remote_connection",
        "PIL.PngImagePlugin",
        "matplotlib.font_manager"
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)