"""
Base Tool Interface for Desktop MCP Plugin System

This module defines the base interface that all tools must implement,
providing a standard structure for plugin discovery, validation, and execution.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Standard tool categories for organization"""
    FILE_OPERATIONS = "file_operations"
    SYSTEM_CONTROL = "system_control"
    MEDIA_PROCESSING = "media_processing"
    WEB_AUTOMATION = "web_automation"
    DEVELOPMENT = "development"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    ENTERTAINMENT = "entertainment"
    UTILITIES = "utilities"
    CUSTOM = "custom"


class ParameterType(Enum):
    """Parameter types for validation"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    PATH = "path"
    URL = "url"
    EMAIL = "email"
    LIST = "list"
    DICT = "dict"
    FILE = "file"
    DIRECTORY = "directory"


@dataclass
class ToolParameter:
    """Tool parameter definition with validation"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None  # Regex pattern for string validation
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate parameter value"""
        if value is None:
            if self.required:
                return False, f"Parameter '{self.name}' is required"
            return True, None
        
        # Type validation
        if self.type == ParameterType.STRING and not isinstance(value, str):
            return False, f"Parameter '{self.name}' must be a string"
        elif self.type == ParameterType.INTEGER and not isinstance(value, int):
            return False, f"Parameter '{self.name}' must be an integer"
        elif self.type == ParameterType.FLOAT and not isinstance(value, (int, float)):
            return False, f"Parameter '{self.name}' must be a number"
        elif self.type == ParameterType.BOOLEAN and not isinstance(value, bool):
            return False, f"Parameter '{self.name}' must be a boolean"
        elif self.type == ParameterType.LIST and not isinstance(value, list):
            return False, f"Parameter '{self.name}' must be a list"
        elif self.type == ParameterType.DICT and not isinstance(value, dict):
            return False, f"Parameter '{self.name}' must be a dictionary"
        
        # Range validation for numbers
        if self.type in [ParameterType.INTEGER, ParameterType.FLOAT] and isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                return False, f"Parameter '{self.name}' must be >= {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Parameter '{self.name}' must be <= {self.max_value}"
        
        # Choice validation
        if self.choices and value not in self.choices:
            return False, f"Parameter '{self.name}' must be one of: {self.choices}"
        
        # Pattern validation for strings
        if self.type == ParameterType.STRING and self.pattern and isinstance(value, str):
            import re
            if not re.match(self.pattern, value):
                return False, f"Parameter '{self.name}' does not match required pattern"
        
        # Path validation
        if self.type in [ParameterType.PATH, ParameterType.FILE, ParameterType.DIRECTORY] and isinstance(value, str):
            from pathlib import Path
            path = Path(value)
            if self.type == ParameterType.FILE and not path.is_file():
                return False, f"File not found: {value}"
            elif self.type == ParameterType.DIRECTORY and not path.is_dir():
                return False, f"Directory not found: {value}"
        
        # URL validation
        if self.type == ParameterType.URL and isinstance(value, str):
            from urllib.parse import urlparse
            parsed = urlparse(value)
            if not all([parsed.scheme, parsed.netloc]):
                return False, f"Invalid URL format: {value}"
        
        # Email validation
        if self.type == ParameterType.EMAIL and isinstance(value, str):
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False, f"Invalid email format: {value}"
        
        return True, None


@dataclass
class ToolMetadata:
    """Tool metadata for discovery and management"""
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: str = "Desktop MCP"
    keywords: List[str] = field(default_factory=list)
    parameters: List[ToolParameter] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)  # Python packages
    platforms: List[str] = field(default_factory=lambda: ["windows", "linux", "darwin"])
    min_python_version: str = "3.10"
    icon: Optional[str] = None
    documentation_url: Optional[str] = None
    examples: List[str] = field(default_factory=list)


@dataclass
class ToolResult:
    """Standardized tool execution result"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat()
        }


class BaseTool(ABC):
    """
    Base class for all Desktop MCP tools.
    
    All tools must inherit from this class and implement the required methods.
    This provides a standard interface for plugin discovery, validation, and execution.
    """
    
    def __init__(self):
        self.metadata = self.get_metadata()
        self.logger = logging.getLogger(f"Tool.{self.metadata.name}")
        self._validate_metadata()
    
    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """
        Return tool metadata including name, description, parameters, etc.
        This method must be implemented by all tools.
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the provided parameters.
        
        Args:
            **kwargs: Tool parameters as defined in metadata
            
        Returns:
            ToolResult: Standardized result object
        """
        pass
    
    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate provided parameters against tool metadata.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        for param in self.metadata.parameters:
            value = kwargs.get(param.name)
            is_valid, error = param.validate(value)
            if not is_valid:
                return False, error
        
        # Check for unexpected parameters
        expected_params = {p.name for p in self.metadata.parameters}
        provided_params = set(kwargs.keys())
        unexpected = provided_params - expected_params
        
        if unexpected:
            return False, f"Unexpected parameters: {unexpected}"
        
        return True, None
    
    def safe_execute(self, **kwargs) -> ToolResult:
        """
        Execute tool with parameter validation and error handling.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult: Execution result with timing and error handling
        """
        start_time = time.time()
        
        try:
            # Validate parameters
            is_valid, error = self.validate_parameters(**kwargs)
            if not is_valid:
                return ToolResult(
                    success=False,
                    message="Parameter validation failed",
                    error=error,
                    execution_time=time.time() - start_time
                )
            
            # Execute tool
            self.logger.info(f"Executing tool '{self.metadata.name}' with parameters: {kwargs}")
            result = self.execute(**kwargs)
            
            # Ensure result has execution time
            result.execution_time = time.time() - start_time
            
            self.logger.info(f"Tool '{self.metadata.name}' completed in {result.execution_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                message="Tool execution failed",
                error=error_msg,
                execution_time=time.time() - start_time
            )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get parameter schema for UI generation"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.metadata.parameters:
            prop = {
                "description": param.description,
                "type": self._param_type_to_json_type(param.type)
            }
            
            if param.default is not None:
                prop["default"] = param.default
            
            if param.choices:
                prop["enum"] = param.choices
            
            if param.min_value is not None:
                prop["minimum"] = param.min_value
            
            if param.max_value is not None:
                prop["maximum"] = param.max_value
            
            if param.pattern:
                prop["pattern"] = param.pattern
            
            schema["properties"][param.name] = prop
            
            if param.required:
                schema["required"].append(param.name)
        
        return schema
    
    def _validate_metadata(self):
        """Validate tool metadata"""
        if not self.metadata.name:
            raise ValueError("Tool name is required")
        
        if not self.metadata.description:
            raise ValueError("Tool description is required")
        
        # Validate parameter names are unique
        param_names = [p.name for p in self.metadata.parameters]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Parameter names must be unique")
    
    def _param_type_to_json_type(self, param_type: ParameterType) -> str:
        """Convert parameter type to JSON schema type"""
        mapping = {
            ParameterType.STRING: "string",
            ParameterType.INTEGER: "integer",
            ParameterType.FLOAT: "number",
            ParameterType.BOOLEAN: "boolean",
            ParameterType.LIST: "array",
            ParameterType.DICT: "object",
            ParameterType.PATH: "string",
            ParameterType.FILE: "string",
            ParameterType.DIRECTORY: "string",
            ParameterType.URL: "string",
            ParameterType.EMAIL: "string"
        }
        return mapping.get(param_type, "string")
    
    def __str__(self) -> str:
        return f"Tool({self.metadata.name})"
    
    def __repr__(self) -> str:
        return f"<Tool: {self.metadata.name} v{self.metadata.version}>"


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.categories: Dict[ToolCategory, List[str]] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        name = tool.metadata.name
        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered, overwriting")
        
        self.tools[name] = tool
        
        # Update category index
        category = tool.metadata.category
        if category not in self.categories:
            self.categories[category] = []
        
        if name not in self.categories[category]:
            self.categories[category].append(name)
        
        logger.info(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get all tools in a category"""
        tool_names = self.categories.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
    
    def search_tools(self, query: str) -> List[BaseTool]:
        """Search tools by name, description, or keywords"""
        query = query.lower()
        results = []
        
        for tool in self.tools.values():
            # Search in name
            if query in tool.metadata.name.lower():
                results.append(tool)
                continue
            
            # Search in description
            if query in tool.metadata.description.lower():
                results.append(tool)
                continue
            
            # Search in keywords
            if any(query in keyword.lower() for keyword in tool.metadata.keywords):
                results.append(tool)
                continue
        
        return results


# Global tool registry instance
tool_registry = ToolRegistry()