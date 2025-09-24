"""
Error Handler for YAML Parser

Handles errors during YAML parsing, validation, and processing operations.
"""

import logging
import traceback
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class YAMLError:
    """Represents a YAML parsing error."""
    
    def __init__(self, error_type: str, message: str, line: Optional[int] = None, 
                 column: Optional[int] = None, context: Optional[str] = None):
        self.error_type = error_type
        self.message = message
        self.line = line
        self.column = column
        self.context = context
        self.timestamp = datetime.now()
        self.traceback = traceback.format_exc()
    
    def __str__(self) -> str:
        location = f"line {self.line}" if self.line else "unknown location"
        if self.column:
            location += f", column {self.column}"
        
        return f"{self.error_type} at {location}: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback
        }


class YAMLErrorHandler:
    """Handles errors during YAML parsing operations."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.errors: List[YAMLError] = []
        self.error_callbacks: List[Callable[[YAMLError], None]] = []
        self.max_errors = self.config.get("max_errors", 100)
        self.continue_on_error = self.config.get("continue_on_error", True)
        self.raise_on_critical = self.config.get("raise_on_critical", True)
        self.log_errors = self.config.get("log_errors", True)
    
    def add_error_callback(self, callback: Callable[[YAMLError], None]):
        """Add a callback function to be called when an error occurs."""
        self.error_callbacks.append(callback)
    
    def handle_error(self, error_type: str, message: str, line: Optional[int] = None,
                    column: Optional[int] = None, context: Optional[str] = None,
                    exception: Optional[Exception] = None) -> bool:
        """
        Handle a YAML parsing error.
        
        Returns True if processing should continue, False otherwise.
        """
        error = YAMLError(error_type, message, line, column, context)
        
        # Add to error list
        self.errors.append(error)
        
        # Log error if enabled
        if self.log_errors:
            logger.error(f"YAML Error: {error}")
        
        # Call error callbacks
        for callback in self.error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
        
        # Check if we should continue
        if len(self.errors) >= self.max_errors:
            logger.error(f"Maximum number of errors ({self.max_errors}) reached. Stopping.")
            return False
        
        # Check if we should raise on critical errors
        if self.raise_on_critical and error_type in ["CRITICAL", "SYNTAX_ERROR", "VALIDATION_ERROR"]:
            raise YAMLParsingError(f"Critical error: {error}")
        
        return self.continue_on_error
    
    def handle_exception(self, stage_name: str, exception: Exception) -> bool:
        """Handle an exception from a parsing stage."""
        error_type = "STAGE_ERROR"
        message = f"Error in {stage_name}: {str(exception)}"
        
        return self.handle_error(error_type, message, exception=exception)
    
    def handle_yaml_error(self, yaml_error: Exception, context: Optional[str] = None) -> bool:
        """Handle a YAML-specific error."""
        error_type = "YAML_SYNTAX_ERROR"
        message = str(yaml_error)
        
        # Try to extract line and column information
        line = None
        column = None
        
        if hasattr(yaml_error, 'problem_mark'):
            line = yaml_error.problem_mark.line + 1
            column = yaml_error.problem_mark.column + 1
        
        return self.handle_error(error_type, message, line, column, context, yaml_error)
    
    def handle_validation_error(self, field: str, message: str, value: Any = None) -> bool:
        """Handle a validation error."""
        error_type = "VALIDATION_ERROR"
        full_message = f"Validation error for field '{field}': {message}"
        if value is not None:
            full_message += f" (value: {value})"
        
        return self.handle_error(error_type, full_message)
    
    def handle_processing_error(self, operation: str, message: str, data: Any = None) -> bool:
        """Handle a processing error."""
        error_type = "PROCESSING_ERROR"
        full_message = f"Processing error in '{operation}': {message}"
        
        return self.handle_error(error_type, full_message)
    
    def get_errors(self) -> List[YAMLError]:
        """Get all recorded errors."""
        return self.errors.copy()
    
    def get_errors_by_type(self, error_type: str) -> List[YAMLError]:
        """Get errors of a specific type."""
        return [error for error in self.errors if error.error_type == error_type]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors."""
        error_counts = {}
        for error in self.errors:
            error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
        
        return {
            "total_errors": len(self.errors),
            "error_counts": error_counts,
            "has_critical_errors": any(e.error_type in ["CRITICAL", "SYNTAX_ERROR"] for e in self.errors),
            "first_error": self.errors[0].to_dict() if self.errors else None,
            "last_error": self.errors[-1].to_dict() if self.errors else None
        }
    
    def clear_errors(self):
        """Clear all recorded errors."""
        self.errors.clear()
    
    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors have been recorded."""
        return any(error.error_type in ["CRITICAL", "SYNTAX_ERROR"] for error in self.errors)
    
    def export_errors(self, filepath: str) -> bool:
        """Export errors to a JSON file."""
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([error.to_dict() for error in self.errors], f, indent=2, default=str)
            logger.info(f"Errors exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export errors to {filepath}: {e}")
            return False


class YAMLParsingError(Exception):
    """Custom exception for YAML parsing errors."""
    
    def __init__(self, message: str, errors: Optional[List[YAMLError]] = None):
        super().__init__(message)
        self.errors = errors or []
    
    def add_error(self, error: YAMLError):
        """Add an error to this exception."""
        self.errors.append(error)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors in this exception."""
        if not self.errors:
            return {"total_errors": 0}
        
        error_counts = {}
        for error in self.errors:
            error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1
        
        return {
            "total_errors": len(self.errors),
            "error_counts": error_counts,
            "has_critical_errors": any(e.error_type in ["CRITICAL", "SYNTAX_ERROR"] for e in self.errors)
        } 