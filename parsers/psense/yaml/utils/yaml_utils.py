"""
YAML Utilities

Utility functions for YAML parsing, validation, and processing operations.
"""

import yaml
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class YAMLUtils:
    """Utility functions for YAML operations."""
    
    def __init__(self):
        self.comment_pattern = re.compile(r'^\s*#.*$')
        self.key_pattern = re.compile(r'^(\s*)([^:]+):\s*(.*)$')
    
    def safe_load_yaml(self, content: str, preserve_order: bool = True) -> Dict[str, Any]:
        """Safely load YAML content with error handling."""
        try:
            if preserve_order:
                # Use OrderedDict to preserve order
                yaml.add_representer(OrderedDict, yaml.representer.SafeRepresenter.represent_dict)
                return yaml.safe_load(content)
            else:
                return yaml.safe_load(content)
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing YAML: {e}")
            raise
    
    def load_yaml_file(self, filepath: Union[str, Path], encoding: str = 'utf-8') -> Dict[str, Any]:
        """Load YAML from file with error handling."""
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            return self.safe_load_yaml(content)
        except FileNotFoundError:
            logger.error(f"YAML file not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Error loading YAML file {filepath}: {e}")
            raise
    
    def extract_comments(self, content: str) -> List[Tuple[int, str]]:
        """Extract comments from YAML content with line numbers."""
        comments = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if self.comment_pattern.match(line):
                comment = line.strip()
                comments.append((line_num, comment))
        
        return comments
    
    def extract_structure_info(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structural information from YAML data."""
        def analyze_structure(data: Any, path: str = "") -> Dict[str, Any]:
            if isinstance(data, dict):
                return {
                    "type": "object",
                    "keys": list(data.keys()),
                    "key_count": len(data),
                    "nested": {k: analyze_structure(v, f"{path}.{k}" if path else k) 
                              for k, v in data.items()}
                }
            elif isinstance(data, list):
                return {
                    "type": "array",
                    "length": len(data),
                    "items": [analyze_structure(item, f"{path}[{i}]") for i, item in enumerate(data)]
                }
            else:
                return {
                    "type": type(data).__name__,
                    "value": str(data)[:100] if data is not None else None
                }
        
        return analyze_structure(yaml_data)
    
    def find_schemas(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Find schema definitions in YAML data (OpenAPI, etc.)."""
        schemas = {}
        
        def extract_schemas(data: Any, path: str = ""):
            if isinstance(data, dict):
                # Look for common schema patterns
                if "components" in data and "schemas" in data["components"]:
                    schemas["openapi_schemas"] = data["components"]["schemas"]
                
                if "definitions" in data:
                    schemas["json_schema_definitions"] = data["definitions"]
                
                if "schemas" in data:
                    schemas["direct_schemas"] = data["schemas"]
                
                # Recursively search
                for key, value in data.items():
                    extract_schemas(value, f"{path}.{key}" if path else key)
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    extract_schemas(item, f"{path}[{i}]")
        
        extract_schemas(yaml_data)
        return schemas
    
    def extract_api_endpoints(self, yaml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract API endpoints from YAML data (OpenAPI, etc.)."""
        endpoints = []
        
        def extract_endpoints(data: Any, path: str = ""):
            if isinstance(data, dict):
                # Look for OpenAPI paths
                if "paths" in data:
                    for endpoint_path, methods in data["paths"].items():
                        for method, details in methods.items():
                            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                                endpoints.append({
                                    "path": endpoint_path,
                                    "method": method.upper(),
                                    "operation_id": details.get("operationId"),
                                    "summary": details.get("summary"),
                                    "description": details.get("description"),
                                    "parameters": details.get("parameters", []),
                                    "responses": details.get("responses", {}),
                                    "tags": details.get("tags", [])
                                })
                
                # Recursively search
                for key, value in data.items():
                    extract_endpoints(value, f"{path}.{key}" if path else key)
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    extract_endpoints(item, f"{path}[{i}]")
        
        extract_endpoints(yaml_data)
        return endpoints
    
    def extract_examples(self, yaml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract examples from YAML data."""
        examples = []
        
        def extract_examples_recursive(data: Any, path: str = ""):
            if isinstance(data, dict):
                # Look for example fields
                if "example" in data:
                    examples.append({
                        "path": path,
                        "example": data["example"],
                        "type": type(data["example"]).__name__
                    })
                
                if "examples" in data:
                    for name, example in data["examples"].items():
                        examples.append({
                            "path": f"{path}.examples.{name}",
                            "example": example,
                            "name": name,
                            "type": type(example).__name__
                        })
                
                # Recursively search
                for key, value in data.items():
                    extract_examples_recursive(value, f"{path}.{key}" if path else key)
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    extract_examples_recursive(item, f"{path}[{i}]")
        
        extract_examples_recursive(yaml_data)
        return examples
    
    def extract_descriptions(self, yaml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract descriptions from YAML data."""
        descriptions = []
        
        def extract_descriptions_recursive(data: Any, path: str = ""):
            if isinstance(data, dict):
                # Look for description fields
                if "description" in data:
                    descriptions.append({
                        "path": path,
                        "description": data["description"],
                        "type": type(data["description"]).__name__
                    })
                
                # Recursively search
                for key, value in data.items():
                    extract_descriptions_recursive(value, f"{path}.{key}" if path else key)
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    extract_descriptions_recursive(item, f"{path}[{i}]")
        
        extract_descriptions_recursive(yaml_data)
        return descriptions
    
    def normalize_structure(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize YAML structure for consistent processing."""
        def normalize_recursive(data: Any):
            if isinstance(data, dict):
                # Convert OrderedDict to regular dict
                if isinstance(data, OrderedDict):
                    data = dict(data)
                
                # Normalize nested structures
                for key, value in data.items():
                    data[key] = normalize_recursive(value)
                
                return data
            
            elif isinstance(data, list):
                return [normalize_recursive(item) for item in data]
            
            else:
                return data
        
        return normalize_recursive(yaml_data)
    
    def resolve_references(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve YAML references ($ref) in the data."""
        def resolve_refs_recursive(data: Any, root_data: Dict[str, Any]):
            if isinstance(data, dict):
                # Check for $ref
                if "$ref" in data:
                    ref_path = data["$ref"]
                    # Simple reference resolution (can be enhanced)
                    if ref_path.startswith("#/"):
                        path_parts = ref_path[2:].split("/")
                        ref_value = root_data
                        for part in path_parts:
                            if isinstance(ref_value, dict) and part in ref_value:
                                ref_value = ref_value[part]
                            else:
                                logger.warning(f"Could not resolve reference: {ref_path}")
                                return data
                        return resolve_refs_recursive(ref_value, root_data)
                
                # Process nested structures
                for key, value in data.items():
                    data[key] = resolve_refs_recursive(value, root_data)
                
                return data
            
            elif isinstance(data, list):
                return [resolve_refs_recursive(item, root_data) for item in data]
            
            else:
                return data
        
        return resolve_refs_recursive(yaml_data, yaml_data)
    
    def validate_yaml_structure(self, yaml_data: Dict[str, Any]) -> List[str]:
        """Validate YAML structure and return validation messages."""
        validation_errors = []
        
        def validate_recursive(data: Any, path: str = ""):
            if isinstance(data, dict):
                # Check for empty keys
                for key in data.keys():
                    if not key or not key.strip():
                        validation_errors.append(f"Empty key found at {path}")
                
                # Recursively validate nested structures
                for key, value in data.items():
                    validate_recursive(value, f"{path}.{key}" if path else key)
            
            elif isinstance(data, list):
                # Allow empty lists in OpenAPI examples and certain contexts
                if not data:
                    # Skip validation for empty lists in examples or certain paths
                    if "example" in path or "examples" in path or "value" in path:
                        pass  # Allow empty lists in examples
                    else:
                        validation_errors.append(f"Empty list found at {path}")
                else:
                    # Validate list items
                    for i, item in enumerate(data):
                        validate_recursive(item, f"{path}[{i}]")
        
        validate_recursive(yaml_data)
        return validation_errors
    
    def convert_to_json_schema(self, yaml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert YAML structure to JSON Schema format."""
        def convert_recursive(data: Any) -> Dict[str, Any]:
            if isinstance(data, dict):
                schema = {"type": "object", "properties": {}}
                
                for key, value in data.items():
                    schema["properties"][key] = convert_recursive(value)
                
                return schema
            
            elif isinstance(data, list):
                if data:
                    schema = {"type": "array", "items": convert_recursive(data[0])}
                else:
                    schema = {"type": "array", "items": {}}
                return schema
            
            elif isinstance(data, str):
                return {"type": "string"}
            
            elif isinstance(data, (int, float)):
                return {"type": "number"}
            
            elif isinstance(data, bool):
                return {"type": "boolean"}
            
            elif data is None:
                return {"type": "null"}
            
            else:
                return {"type": "string"}
        
        return convert_recursive(yaml_data)
    
    def merge_yaml_files(self, filepaths: List[Union[str, Path]]) -> Dict[str, Any]:
        """Merge multiple YAML files into a single structure."""
        merged_data = {}
        
        for filepath in filepaths:
            try:
                file_data = self.load_yaml_file(filepath)
                merged_data.update(file_data)
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
        
        return merged_data
    
    def diff_yaml_structures(self, yaml1: Dict[str, Any], yaml2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two YAML structures and return differences."""
        def compare_recursive(data1: Any, data2: Any, path: str = "") -> Dict[str, Any]:
            if type(data1) != type(data2):
                return {
                    "type": "type_mismatch",
                    "path": path,
                    "value1": data1,
                    "value2": data2,
                    "type1": type(data1).__name__,
                    "type2": type(data2).__name__
                }
            
            if isinstance(data1, dict):
                differences = {}
                
                # Check keys in data1 but not in data2
                for key in data1:
                    if key not in data2:
                        differences[f"missing_in_2.{key}"] = {
                            "type": "missing_key",
                            "path": f"{path}.{key}",
                            "value": data1[key]
                        }
                
                # Check keys in data2 but not in data1
                for key in data2:
                    if key not in data1:
                        differences[f"missing_in_1.{key}"] = {
                            "type": "missing_key",
                            "path": f"{path}.{key}",
                            "value": data2[key]
                        }
                
                # Compare common keys
                for key in set(data1.keys()) & set(data2.keys()):
                    diff = compare_recursive(data1[key], data2[key], f"{path}.{key}")
                    if diff:
                        differences[key] = diff
                
                return differences if differences else None
            
            elif isinstance(data1, list):
                if len(data1) != len(data2):
                    return {
                        "type": "length_mismatch",
                        "path": path,
                        "length1": len(data1),
                        "length2": len(data2)
                    }
                
                differences = []
                for i, (item1, item2) in enumerate(zip(data1, data2)):
                    diff = compare_recursive(item1, item2, f"{path}[{i}]")
                    if diff:
                        differences.append(diff)
                
                return differences if differences else None
            
            else:
                if data1 != data2:
                    return {
                        "type": "value_mismatch",
                        "path": path,
                        "value1": data1,
                        "value2": data2
                    }
                
                return None
        
        return compare_recursive(yaml1, yaml2) or {} 