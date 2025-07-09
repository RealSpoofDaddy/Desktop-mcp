"""
Command Parser for Desktop MCP

Translates natural language commands into tool executions using NLP techniques,
pattern matching, and intent recognition.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

# Try to import NLP libraries (optional dependencies)
try:
    import spacy
    SPACY_AVAILABLE = True
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Fallback to basic spacy model
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False

try:
    from fuzzywuzzy import fuzz, process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

from ..tools.base_tool import BaseTool, tool_registry, ToolCategory

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """Parsed command structure"""
    intent: str
    action: str
    entities: Dict[str, Any]
    confidence: float
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    alternatives: Optional[List[str]] = None


@dataclass
class CommandPattern:
    """Command pattern for matching"""
    pattern: str
    intent: str
    action: str
    tool_name: str
    parameter_mapping: Dict[str, str]
    examples: List[str]


class CommandParser:
    """
    Natural language command parser for Desktop MCP.
    
    Features:
    - Intent recognition using patterns and NLP
    - Entity extraction (files, apps, parameters)
    - Tool routing and parameter mapping
    - Context awareness and command memory
    - Fuzzy matching for typos and variations
    """
    
    def __init__(self):
        self.patterns: List[CommandPattern] = []
        self.command_history: List[ParsedCommand] = []
        self.context: Dict[str, Any] = {}
        self.tool_registry = tool_registry
        
        # Load built-in patterns
        self._load_builtin_patterns()
        
        logger.info("Command parser initialized")
        if SPACY_AVAILABLE:
            logger.info("SpaCy NLP enabled")
        if FUZZY_AVAILABLE:
            logger.info("Fuzzy matching enabled")
    
    def parse_command(self, command: str) -> ParsedCommand:
        """
        Parse a natural language command into structured format.
        
        Args:
            command: Natural language command string
            
        Returns:
            ParsedCommand: Parsed command with intent, action, and parameters
        """
        command = command.strip().lower()
        
        if not command:
            return ParsedCommand(
                intent="unknown",
                action="none",
                entities={},
                confidence=0.0
            )
        
        logger.info(f"Parsing command: {command}")
        
        # Try pattern matching first
        pattern_result = self._match_patterns(command)
        if pattern_result.confidence > 0.7:
            logger.info(f"Pattern match found: {pattern_result.tool_name}")
            return pattern_result
        
        # Try NLP-based parsing if available
        if SPACY_AVAILABLE:
            nlp_result = self._parse_with_nlp(command)
            if nlp_result.confidence > pattern_result.confidence:
                logger.info(f"NLP match found: {nlp_result.tool_name}")
                return nlp_result
        
        # Try tool name matching
        tool_result = self._match_tool_names(command)
        if tool_result.confidence > pattern_result.confidence:
            logger.info(f"Tool name match found: {tool_result.tool_name}")
            return tool_result
        
        # Return best result or unknown
        best_result = max([pattern_result, tool_result], key=lambda x: x.confidence)
        
        if best_result.confidence < 0.3:
            return ParsedCommand(
                intent="unknown",
                action="help",
                entities={"original_command": command},
                confidence=0.0,
                alternatives=self._suggest_alternatives(command)
            )
        
        return best_result
    
    def _match_patterns(self, command: str) -> ParsedCommand:
        """Match command against predefined patterns"""
        best_match = None
        best_confidence = 0.0
        
        for pattern in self.patterns:
            # Use regex matching
            regex_pattern = self._convert_pattern_to_regex(pattern.pattern)
            match = re.search(regex_pattern, command, re.IGNORECASE)
            
            if match:
                confidence = 0.9  # High confidence for exact pattern match
                entities = self._extract_entities_from_match(match, pattern)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = ParsedCommand(
                        intent=pattern.intent,
                        action=pattern.action,
                        entities=entities,
                        confidence=confidence,
                        tool_name=pattern.tool_name,
                        parameters=self._map_parameters(entities, pattern.parameter_mapping)
                    )
            
            # Also try fuzzy matching if available
            if FUZZY_AVAILABLE:
                for example in pattern.examples:
                    similarity = fuzz.ratio(command, example.lower()) / 100.0
                    if similarity > 0.8 and similarity > best_confidence:
                        best_confidence = similarity
                        # Extract entities from the command based on the pattern
                        entities = self._extract_entities_fuzzy(command, pattern)
                        best_match = ParsedCommand(
                            intent=pattern.intent,
                            action=pattern.action,
                            entities=entities,
                            confidence=similarity,
                            tool_name=pattern.tool_name,
                            parameters=self._map_parameters(entities, pattern.parameter_mapping)
                        )
        
        return best_match or ParsedCommand(
            intent="unknown", action="none", entities={}, confidence=0.0
        )
    
    def _parse_with_nlp(self, command: str) -> ParsedCommand:
        """Parse command using spaCy NLP"""
        if not SPACY_AVAILABLE:
            return ParsedCommand(intent="unknown", action="none", entities={}, confidence=0.0)
        
        doc = nlp(command)
        
        # Extract entities
        entities = {}
        for ent in doc.ents:
            entities[ent.label_.lower()] = ent.text
        
        # Extract file paths and app names
        entities.update(self._extract_common_entities(command))
        
        # Determine intent based on verbs and keywords
        intent, action, confidence = self._determine_intent(doc)
        
        # Try to match to a tool
        tool_name = self._find_best_tool_match(intent, action, entities)
        
        return ParsedCommand(
            intent=intent,
            action=action,
            entities=entities,
            confidence=confidence,
            tool_name=tool_name,
            parameters=self._infer_parameters(entities, tool_name)
        )
    
    def _match_tool_names(self, command: str) -> ParsedCommand:
        """Match command against tool names and descriptions"""
        best_tool = None
        best_confidence = 0.0
        
        for tool_name, tool in self.tool_registry.tools.items():
            # Check tool name
            if tool_name.lower() in command:
                confidence = 0.8
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_tool = tool
            
            # Check keywords
            for keyword in tool.metadata.keywords:
                if keyword.lower() in command:
                    confidence = 0.6
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_tool = tool
            
            # Fuzzy match tool name and description
            if FUZZY_AVAILABLE:
                name_similarity = fuzz.partial_ratio(command, tool_name.lower()) / 100.0
                desc_similarity = fuzz.partial_ratio(command, tool.metadata.description.lower()) / 100.0
                
                similarity = max(name_similarity, desc_similarity)
                if similarity > 0.7 and similarity > best_confidence:
                    best_confidence = similarity
                    best_tool = tool
        
        if best_tool:
            entities = self._extract_common_entities(command)
            return ParsedCommand(
                intent="execute_tool",
                action="run",
                entities=entities,
                confidence=best_confidence,
                tool_name=best_tool.metadata.name,
                parameters=self._infer_parameters(entities, best_tool.metadata.name)
            )
        
        return ParsedCommand(intent="unknown", action="none", entities={}, confidence=0.0)
    
    def _extract_common_entities(self, command: str) -> Dict[str, Any]:
        """Extract common entities like file paths, URLs, etc."""
        entities = {}
        
        # Extract file paths
        path_patterns = [
            r'([a-zA-Z]:[\\\/][^\s]+)',  # Windows paths
            r'(\/[^\s]+)',               # Unix paths
            r'(\~\/[^\s]+)',             # Home directory paths
            r'(\.\/[^\s]+)',             # Relative paths
            r'(\.\.[\\\/][^\s]+)'        # Parent directory paths
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, command)
            if matches:
                entities['file_paths'] = matches
                break
        
        # Extract URLs
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, command)
        if urls:
            entities['urls'] = urls
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, command, re.IGNORECASE)
        if emails:
            entities['emails'] = emails
        
        # Extract numbers
        numbers = re.findall(r'\b\d+\b', command)
        if numbers:
            entities['numbers'] = [int(n) for n in numbers]
        
        # Extract quoted strings
        quoted = re.findall(r'"([^"]*)"', command)
        if quoted:
            entities['quoted_strings'] = quoted
        
        return entities
    
    def _determine_intent(self, doc) -> Tuple[str, str, float]:
        """Determine intent from spaCy document"""
        verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
        
        # Intent mapping based on verbs
        intent_mapping = {
            "open": ("application", "launch"),
            "start": ("application", "launch"),
            "launch": ("application", "launch"),
            "run": ("application", "launch"),
            "close": ("application", "close"),
            "quit": ("application", "close"),
            "exit": ("application", "close"),
            "copy": ("file", "copy"),
            "move": ("file", "move"),
            "delete": ("file", "delete"),
            "remove": ("file", "delete"),
            "create": ("file", "create"),
            "make": ("file", "create"),
            "zip": ("archive", "create"),
            "compress": ("archive", "create"),
            "extract": ("archive", "extract"),
            "unzip": ("archive", "extract"),
            "search": ("web", "search"),
            "browse": ("web", "navigate"),
            "visit": ("web", "navigate"),
            "download": ("web", "download"),
            "take": ("system", "screenshot"),
            "capture": ("system", "screenshot"),
            "monitor": ("system", "monitor"),
            "check": ("system", "status")
        }
        
        for verb in verbs:
            if verb in intent_mapping:
                intent, action = intent_mapping[verb]
                return intent, action, 0.8
        
        return "unknown", "none", 0.0
    
    def _find_best_tool_match(self, intent: str, action: str, entities: Dict[str, Any]) -> Optional[str]:
        """Find the best tool match for given intent and action"""
        # Simple tool matching based on category and action
        category_mapping = {
            "file": ToolCategory.FILE_OPERATIONS,
            "application": ToolCategory.SYSTEM_CONTROL,
            "archive": ToolCategory.UTILITIES,
            "web": ToolCategory.WEB_AUTOMATION,
            "system": ToolCategory.SYSTEM_CONTROL
        }
        
        category = category_mapping.get(intent)
        if not category:
            return None
        
        tools = self.tool_registry.get_tools_by_category(category)
        
        # Find tool with matching action in name or description
        for tool in tools:
            if action in tool.metadata.name.lower() or action in tool.metadata.description.lower():
                return tool.metadata.name
        
        # Return first tool in category if no specific match
        return tools[0].metadata.name if tools else None
    
    def _convert_pattern_to_regex(self, pattern: str) -> str:
        """Convert pattern string to regex"""
        # Replace placeholders with regex groups
        pattern = pattern.replace("{file}", r"([^\s]+)")
        pattern = pattern.replace("{app}", r"([a-zA-Z]+(?:\s+[a-zA-Z]+)*)")
        pattern = pattern.replace("{text}", r"(.+)")
        pattern = pattern.replace("{number}", r"(\d+)")
        pattern = pattern.replace("{path}", r"([^\s]+)")
        
        return pattern
    
    def _extract_entities_from_match(self, match, pattern: CommandPattern) -> Dict[str, Any]:
        """Extract entities from regex match"""
        entities = {}
        groups = match.groups()
        
        # Map regex groups to entity types based on pattern
        if "{file}" in pattern.pattern:
            entities["file"] = groups[0] if groups else None
        if "{app}" in pattern.pattern:
            entities["app"] = groups[0] if groups else None
        if "{text}" in pattern.pattern:
            entities["text"] = groups[0] if groups else None
        
        return entities
    
    def _extract_entities_fuzzy(self, command: str, pattern: CommandPattern) -> Dict[str, Any]:
        """Extract entities using fuzzy matching"""
        # Simple entity extraction for fuzzy matches
        return self._extract_common_entities(command)
    
    def _map_parameters(self, entities: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map entities to tool parameters"""
        parameters = {}
        
        for entity_key, param_name in mapping.items():
            if entity_key in entities:
                parameters[param_name] = entities[entity_key]
        
        return parameters
    
    def _infer_parameters(self, entities: Dict[str, Any], tool_name: Optional[str]) -> Dict[str, Any]:
        """Infer parameters for a tool based on entities"""
        if not tool_name:
            return {}
        
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return {}
        
        parameters = {}
        
        # Simple parameter inference
        for param in tool.metadata.parameters:
            param_name = param.name.lower()
            
            # Map common entity types to parameters
            if "path" in param_name or "file" in param_name:
                if "file_paths" in entities and entities["file_paths"]:
                    parameters[param.name] = entities["file_paths"][0]
                elif "file" in entities:
                    parameters[param.name] = entities["file"]
            
            elif "url" in param_name:
                if "urls" in entities and entities["urls"]:
                    parameters[param.name] = entities["urls"][0]
            
            elif "text" in param_name or "message" in param_name:
                if "text" in entities:
                    parameters[param.name] = entities["text"]
                elif "quoted_strings" in entities and entities["quoted_strings"]:
                    parameters[param.name] = entities["quoted_strings"][0]
            
            elif "number" in param_name or "count" in param_name:
                if "numbers" in entities and entities["numbers"]:
                    parameters[param.name] = entities["numbers"][0]
        
        return parameters
    
    def _suggest_alternatives(self, command: str) -> List[str]:
        """Suggest alternative commands for unknown input"""
        suggestions = []
        
        if FUZZY_AVAILABLE:
            # Get all tool names and common patterns
            tool_names = list(self.tool_registry.tools.keys())
            common_commands = [
                "open blender", "take screenshot", "list files", "search web",
                "copy files", "move files", "create zip", "monitor system"
            ]
            
            all_options = tool_names + common_commands
            
            # Find closest matches
            matches = process.extract(command, all_options, limit=3)
            suggestions = [match[0] for match in matches if match[1] > 60]
        
        return suggestions
    
    def _load_builtin_patterns(self):
        """Load built-in command patterns"""
        patterns = [
            # Application control
            CommandPattern(
                pattern=r"open {app}",
                intent="application",
                action="launch",
                tool_name="open_application",
                parameter_mapping={"app": "app_name"},
                examples=["open blender", "open chrome", "open vscode"]
            ),
            CommandPattern(
                pattern=r"start {app}",
                intent="application", 
                action="launch",
                tool_name="open_application",
                parameter_mapping={"app": "app_name"},
                examples=["start blender", "start browser"]
            ),
            
            # File operations
            CommandPattern(
                pattern=r"copy {file} to {path}",
                intent="file",
                action="copy",
                tool_name="copy_files",
                parameter_mapping={"file": "source_path", "path": "destination_path"},
                examples=["copy document.txt to backup folder"]
            ),
            CommandPattern(
                pattern=r"move {file} to {path}",
                intent="file",
                action="move", 
                tool_name="move_files",
                parameter_mapping={"file": "source_path", "path": "destination_path"},
                examples=["move photos to pictures folder"]
            ),
            
            # System operations
            CommandPattern(
                pattern=r"take screenshot",
                intent="system",
                action="screenshot",
                tool_name="take_screenshot",
                parameter_mapping={},
                examples=["take screenshot", "capture screen"]
            ),
            CommandPattern(
                pattern=r"check system",
                intent="system",
                action="monitor",
                tool_name="get_system_information",
                parameter_mapping={},
                examples=["check system status", "monitor system"]
            ),
            
            # Web operations
            CommandPattern(
                pattern=r"search for {text}",
                intent="web",
                action="search",
                tool_name="search_web",
                parameter_mapping={"text": "query"},
                examples=["search for python tutorials"]
            ),
            CommandPattern(
                pattern=r"browse {text}",
                intent="web",
                action="navigate",
                tool_name="navigate_to_website",
                parameter_mapping={"text": "url"},
                examples=["browse github.com"]
            )
        ]
        
        self.patterns.extend(patterns)
        logger.info(f"Loaded {len(patterns)} built-in command patterns")
    
    def add_custom_pattern(self, pattern: CommandPattern):
        """Add a custom command pattern"""
        self.patterns.append(pattern)
        logger.info(f"Added custom pattern: {pattern.pattern}")
    
    def update_context(self, key: str, value: Any):
        """Update command context"""
        self.context[key] = value
    
    def get_command_history(self, limit: int = 10) -> List[ParsedCommand]:
        """Get recent command history"""
        return self.command_history[-limit:]
    
    def remember_command(self, parsed_command: ParsedCommand):
        """Remember a successfully parsed command"""
        self.command_history.append(parsed_command)
        
        # Keep only recent history
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-50:]


# Global command parser instance
command_parser = CommandParser()