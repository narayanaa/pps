"""
YAML Parser

Comprehensive YAML parser for IDE Services and configuration files.
Follows the same architecture as the PDF parser with stages and utilities.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging

from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.table import Table
from doc.psense.document.image import Image

from .config_manager import YAMLConfigManager
from .error_handler import YAMLErrorHandler, YAMLParsingError
from .utils.yaml_utils import YAMLUtils

logger = logging.getLogger(__name__)


class YAMLParser:
    """
    Comprehensive YAML parser for IDE Services and configuration files.
    
    Features:
    - Robust error handling and validation
    - Schema extraction and validation
    - API endpoint extraction (OpenAPI)
    - Example and description extraction
    - Structure normalization and reference resolution
    - Conversion to canonical Document format
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """Initialize the YAML parser with configuration."""
        if config_file is None:
            config_file = "acme_ai_hub/config/parsers/yaml_config.yaml"
        self.config_manager = YAMLConfigManager(config_file)
        self.error_handler = YAMLErrorHandler(self.config_manager.get_error_handling_config())
        self.yaml_utils = YAMLUtils()
        
        # Validate configuration
        if not self.config_manager.validate_config():
            logger.warning("YAML parser configuration validation failed, using defaults")
        
        logger.info("YAML Parser initialized successfully")
    
    def parse(self, filepath: Union[str, Path]) -> Document:
        """
        Parse a YAML file and return a canonical doc.psense.document.Document object.
        
        Args:
            filepath: Path to the YAML file to parse
            
        Returns:
            Document: Canonical document representation of the YAML content
            
        Raises:
            YAMLParsingError: If critical parsing errors occur
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"YAML file not found: {filepath}")
        
        logger.info(f"Parsing YAML file: {filepath}")
        
        try:
            # Start with minimal metadata
            canonical_doc = Document(title=filepath.stem)
            canonical_doc.url = str(filepath)
            canonical_doc.created_date = datetime.now()
            
            # Load and parse YAML content
            yaml_data = self._load_yaml_content(filepath)
            
            # Extract metadata
            self._extract_metadata(canonical_doc, yaml_data, filepath)
            
            # Extract structure information
            self._extract_structure(canonical_doc, yaml_data)
            
            # Extract schemas and API information
            self._extract_schemas_and_apis(canonical_doc, yaml_data)
            
            # Extract examples and descriptions
            self._extract_examples_and_descriptions(canonical_doc, yaml_data)
            
            # Convert to structured content
            self._convert_to_structured_content(canonical_doc, yaml_data)
            
            # Add any parsing errors to the document
            if self.error_handler.has_errors():
                error_summary = self.error_handler.get_error_summary()
                canonical_doc.add_error(f"YAML parsing errors: {error_summary}")
            
            logger.info(f"Successfully parsed YAML file: {filepath}")
            return canonical_doc
            
        except Exception as e:
            logger.error(f"Failed to parse YAML file {filepath}: {e}")
            self.error_handler.handle_exception("YAMLParser.parse", e)
            raise YAMLParsingError(f"Failed to parse YAML file: {e}")
    
    def parse_content(self, content: str, source_name: str = "yaml_content") -> Document:
        """
        Parse YAML content string and return a canonical Document object.
        
        Args:
            content: YAML content as string
            source_name: Name for the source (used in document title)
            
        Returns:
            Document: Canonical document representation
        """
        logger.info(f"Parsing YAML content: {source_name}")
        
        try:
            # Create canonical document
            canonical_doc = Document(title=source_name)
            canonical_doc.created_date = datetime.now()
            
            # Parse YAML content
            yaml_data = self.yaml_utils.safe_load_yaml(content)
            
            # Extract metadata
            self._extract_metadata(canonical_doc, yaml_data, source_name)
            
            # Extract structure information
            self._extract_structure(canonical_doc, yaml_data)
            
            # Extract schemas and API information
            self._extract_schemas_and_apis(canonical_doc, yaml_data)
            
            # Extract examples and descriptions
            self._extract_examples_and_descriptions(canonical_doc, yaml_data)
            
            # Convert to structured content
            self._convert_to_structured_content(canonical_doc, yaml_data)
            
            # Add any parsing errors
            if self.error_handler.has_errors():
                error_summary = self.error_handler.get_error_summary()
                canonical_doc.add_error(f"YAML parsing errors: {error_summary}")
            
            logger.info(f"Successfully parsed YAML content: {source_name}")
            return canonical_doc
            
        except Exception as e:
            logger.error(f"Failed to parse YAML content {source_name}: {e}")
            self.error_handler.handle_exception("YAMLParser.parse_content", e)
            raise YAMLParsingError(f"Failed to parse YAML content: {e}")
    
    def _load_yaml_content(self, filepath: Path) -> Dict[str, Any]:
        """Load YAML content from file with error handling."""
        try:
            # Load raw content
            with open(filepath, 'r', encoding=self.config_manager.get_setting("parsing.encoding", "utf-8")) as f:
                content = f.read()
            
            # Parse YAML
            yaml_data = self.yaml_utils.safe_load_yaml(
                content, 
                preserve_order=self.config_manager.get_setting("parsing.preserve_order", True)
            )
            
            # Normalize structure if enabled
            if self.config_manager.get_setting("processing.normalize_structure", True):
                yaml_data = self.yaml_utils.normalize_structure(yaml_data)
            
            # Resolve references if enabled
            if self.config_manager.get_setting("processing.resolve_references", True):
                yaml_data = self.yaml_utils.resolve_references(yaml_data)
            
            # Validate structure
            validation_errors = self.yaml_utils.validate_yaml_structure(yaml_data)
            for error in validation_errors:
                self.error_handler.handle_validation_error("structure", error)
            
            return yaml_data
            
        except yaml.YAMLError as e:
            self.error_handler.handle_yaml_error(e, f"File: {filepath}")
            raise
        except Exception as e:
            self.error_handler.handle_processing_error("load_yaml_content", str(e))
            raise
    
    def _extract_metadata(self, document: Document, yaml_data: Dict[str, Any], source: Union[str, Path]):
        """Extract metadata from YAML data and add to document."""
        if not self.config_manager.get_setting("processing.extract_metadata", True):
            return
        
        metadata = {
            "source": str(source),
            "parsed_at": datetime.now().isoformat(),
            "yaml_version": "1.2",  # Default YAML version
            "structure_type": self._determine_structure_type(yaml_data)
        }
        
        # Extract OpenAPI metadata if present
        if "openapi" in yaml_data:
            metadata["openapi_version"] = yaml_data["openapi"]
            metadata["info"] = yaml_data.get("info", {})
        
        # Extract other common metadata fields
        for field in ["title", "version", "description", "author", "license"]:
            if field in yaml_data:
                metadata[field] = yaml_data[field]
        
        document.metadata = metadata
    
    def _determine_structure_type(self, yaml_data: Dict[str, Any]) -> str:
        """Determine the type of YAML structure."""
        if "openapi" in yaml_data:
            return "openapi"
        elif "swagger" in yaml_data:
            return "swagger"
        elif "components" in yaml_data and "schemas" in yaml_data["components"]:
            return "api_specification"
        elif "paths" in yaml_data:
            return "api_endpoints"
        elif "definitions" in yaml_data:
            return "json_schema"
        else:
            return "configuration"
    
    def _extract_structure(self, document: Document, yaml_data: Dict[str, Any]):
        """Extract structure information and create document chapters."""
        structure_info = self.yaml_utils.extract_structure_info(yaml_data)
        
        # Create main structure chapter
        structure_chapter = Chapter(title="YAML Structure", sections=[], number=1)
        
        # Add structure overview section
        overview_section = Section(title="Structure Overview", content=[])
        overview_text = f"YAML structure type: {structure_info.get('type', 'unknown')}\n"
        overview_text += f"Key count: {structure_info.get('key_count', 0)}\n"
        overview_text += f"Keys: {', '.join(structure_info.get('keys', []))}"
        
        overview_section.content.append(Paragraph(text=overview_text))
        structure_chapter.sections.append(overview_section)
        
        # Add detailed structure section
        if "nested" in structure_info:
            details_section = Section(title="Detailed Structure", content=[])
            details_text = json.dumps(structure_info["nested"], indent=2)
            details_section.content.append(Paragraph(text=details_text))
            structure_chapter.sections.append(details_section)
        
        document.add_chapter(structure_chapter)
    
    def _extract_schemas_and_apis(self, document: Document, yaml_data: Dict[str, Any]):
        """Extract schemas and API information."""
        if not self.config_manager.get_setting("processing.extract_schemas", True):
            return
        
        # Extract schemas
        schemas = self.yaml_utils.find_schemas(yaml_data)
        
        if schemas:
            schemas_chapter = Chapter(title="Schemas and APIs", sections=[], number=2)
            
            # Add schemas section
            if "openapi_schemas" in schemas:
                schemas_section = Section(title="OpenAPI Schemas", content=[])
                schemas_text = f"Found {len(schemas['openapi_schemas'])} OpenAPI schemas:\n"
                for schema_name in schemas['openapi_schemas'].keys():
                    schemas_text += f"- {schema_name}\n"
                schemas_section.content.append(Paragraph(text=schemas_text))
                schemas_chapter.sections.append(schemas_section)
            
            # Add API endpoints section
            endpoints = self.yaml_utils.extract_api_endpoints(yaml_data)
            if endpoints:
                endpoints_section = Section(title="API Endpoints", content=[])
                endpoints_text = f"Found {len(endpoints)} API endpoints:\n"
                for endpoint in endpoints[:10]:  # Limit to first 10
                    endpoints_text += f"- {endpoint['method']} {endpoint['path']}\n"
                if len(endpoints) > 10:
                    endpoints_text += f"... and {len(endpoints) - 10} more endpoints"
                endpoints_section.content.append(Paragraph(text=endpoints_text))
                schemas_chapter.sections.append(endpoints_section)
            
            document.add_chapter(schemas_chapter)
    
    def _extract_examples_and_descriptions(self, document: Document, yaml_data: Dict[str, Any]):
        """Extract examples and descriptions."""
        if not self.config_manager.get_setting("processing.extract_examples", True):
            return
        
        examples = self.yaml_utils.extract_examples(yaml_data)
        descriptions = self.yaml_utils.extract_descriptions(yaml_data)
        
        if examples or descriptions:
            content_chapter = Chapter(title="Content Information", sections=[], number=3)
            
            # Add examples section
            if examples:
                examples_section = Section(title="Examples", content=[])
                examples_text = f"Found {len(examples)} examples:\n"
                for example in examples[:5]:  # Limit to first 5
                    examples_text += f"- {example['path']}: {example['type']}\n"
                if len(examples) > 5:
                    examples_text += f"... and {len(examples) - 5} more examples"
                examples_section.content.append(Paragraph(text=examples_text))
                content_chapter.sections.append(examples_section)
            
            # Add descriptions section
            if descriptions:
                descriptions_section = Section(title="Descriptions", content=[])
                descriptions_text = f"Found {len(descriptions)} descriptions:\n"
                for desc in descriptions[:5]:  # Limit to first 5
                    descriptions_text += f"- {desc['path']}: {desc['description'][:100]}...\n"
                if len(descriptions) > 5:
                    descriptions_text += f"... and {len(descriptions) - 5} more descriptions"
                descriptions_section.content.append(Paragraph(text=descriptions_text))
                content_chapter.sections.append(descriptions_section)
            
            document.add_chapter(content_chapter)
    
    def _convert_to_structured_content(self, document: Document, yaml_data: Dict[str, Any]):
        """Convert YAML data to structured content in the document."""
        content_chapter = Chapter(title="YAML Content", sections=[], number=4)
        
        # Convert YAML to structured text
        structured_text = self._yaml_to_structured_text(yaml_data)
        
        # Create content section
        content_section = Section(title="Full Content", content=[])
        content_section.content.append(Paragraph(text=structured_text))
        content_chapter.sections.append(content_section)
        
        document.add_chapter(content_chapter)
    
    def _yaml_to_structured_text(self, yaml_data: Dict[str, Any], max_depth: int = None) -> str:
        """Convert YAML data to structured text representation."""
        if max_depth is None:
            max_depth = self.config_manager.get_setting("output.max_depth", 10)
        
        def convert_recursive(data: Any, depth: int = 0, prefix: str = "") -> str:
            if depth > max_depth:
                return f"{prefix}... (max depth reached)\n"
            
            if isinstance(data, dict):
                result = ""
                for key, value in data.items():
                    key_str = f"{prefix}{key}:"
                    if isinstance(value, (dict, list)):
                        result += f"{key_str}\n"
                        result += convert_recursive(value, depth + 1, prefix + "  ")
                    else:
                        result += f"{key_str} {value}\n"
                return result
            
            elif isinstance(data, list):
                result = ""
                for i, item in enumerate(data):
                    if isinstance(item, (dict, list)):
                        result += f"{prefix}- \n"
                        result += convert_recursive(item, depth + 1, prefix + "  ")
                    else:
                        result += f"{prefix}- {item}\n"
                return result
            
            else:
                return f"{prefix}{data}\n"
        
        return convert_recursive(yaml_data)
    
    def get_parsing_summary(self) -> Dict[str, Any]:
        """Get a summary of the parsing operation."""
        return {
            "config": self.config_manager.config,
            "errors": self.error_handler.get_error_summary(),
            "has_errors": self.error_handler.has_errors(),
            "has_critical_errors": self.error_handler.has_critical_errors()
        }
    
    def export_errors(self, filepath: str) -> bool:
        """Export parsing errors to a file."""
        return self.error_handler.export_errors(filepath)
    
    def clear_errors(self):
        """Clear all recorded errors."""
        self.error_handler.clear_errors() 