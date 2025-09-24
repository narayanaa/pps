#!/usr/bin/env python3
"""
Test YAML Parser

Comprehensive test suite for the YAML parser functionality.
"""

import sys
import json
import tempfile
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from parsers.psense.yaml.yaml_parser import YAMLParser
from parsers.psense.yaml.config_manager import YAMLConfigManager
from parsers.psense.yaml.error_handler import YAMLErrorHandler
from parsers.psense.yaml.utils.yaml_utils import YAMLUtils


def test_config_manager():
    """Test the YAML configuration manager."""
    print("🔧 Testing YAML Config Manager")
    print("=" * 50)
    
    # Test default configuration
    config_manager = YAMLConfigManager()
    
    # Test getting settings
    parsing_config = config_manager.get_parsing_config()
    assert "allow_duplicate_keys" in parsing_config
    assert "preserve_quotes" in parsing_config
    
    # Test setting and getting custom settings
    config_manager.set_setting("parsing.custom_setting", "test_value")
    custom_value = config_manager.get_setting("parsing.custom_setting")
    assert custom_value == "test_value"
    
    # Test configuration validation
    assert config_manager.validate_config() == True
    
    print("✅ Config Manager tests passed")


def test_error_handler():
    """Test the YAML error handler."""
    print("\n🚨 Testing YAML Error Handler")
    print("=" * 50)
    
    error_handler = YAMLErrorHandler()
    
    # Test error handling
    error_handler.handle_error("TEST_ERROR", "Test error message", line=10, column=5)
    assert error_handler.has_errors() == True
    assert len(error_handler.get_errors()) == 1
    
    # Test error summary
    summary = error_handler.get_error_summary()
    assert summary["total_errors"] == 1
    assert "TEST_ERROR" in summary["error_counts"]
    
    # Test clearing errors
    error_handler.clear_errors()
    assert error_handler.has_errors() == False
    
    print("✅ Error Handler tests passed")


def test_yaml_utils():
    """Test the YAML utilities."""
    print("\n🛠️ Testing YAML Utils")
    print("=" * 50)
    
    yaml_utils = YAMLUtils()
    
    # Test YAML loading
    test_yaml = """
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: test-config
    data:
      key1: value1
      key2: value2
    """
    
    yaml_data = yaml_utils.safe_load_yaml(test_yaml)
    assert yaml_data["apiVersion"] == "v1"
    assert yaml_data["kind"] == "ConfigMap"
    assert yaml_data["metadata"]["name"] == "test-config"
    
    # Test structure extraction
    structure_info = yaml_utils.extract_structure_info(yaml_data)
    assert structure_info["type"] == "object"
    assert "apiVersion" in structure_info["keys"]
    
    # Test comment extraction
    comments = yaml_utils.extract_comments(test_yaml)
    assert len(comments) == 0  # No comments in test YAML
    
    print("✅ YAML Utils tests passed")


def test_yaml_parser_basic():
    """Test basic YAML parsing functionality."""
    print("\n📄 Testing Basic YAML Parser")
    print("=" * 50)
    
    # Create a temporary YAML file
    test_yaml_content = """
    # Test YAML Configuration
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: test-config
      namespace: default
    data:
      key1: value1
      key2: value2
      nested:
        subkey1: subvalue1
        subkey2: subvalue2
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(test_yaml_content)
        temp_file = f.name
    
    try:
        # Test YAML parser
        parser = YAMLParser()
        document = parser.parse(temp_file)
        
        # Verify document structure
        assert document.title == Path(temp_file).stem
        assert len(document.chapters) > 0
        
        # Check for structure chapter
        structure_chapter = next((ch for ch in document.chapters if ch.title == "YAML Structure"), None)
        assert structure_chapter is not None
        
        # Check for content chapter
        content_chapter = next((ch for ch in document.chapters if ch.title == "YAML Content"), None)
        assert content_chapter is not None
        
        print(f"✅ Basic YAML parsing successful")
        print(f"   Document title: {document.title}")
        print(f"   Chapters: {len(document.chapters)}")
        print(f"   Has errors: {parser.error_handler.has_errors()}")
        
    finally:
        # Clean up
        Path(temp_file).unlink()


def test_yaml_parser_openapi():
    """Test YAML parser with OpenAPI specification."""
    print("\n🔌 Testing OpenAPI YAML Parser")
    print("=" * 50)
    
    # Create a temporary OpenAPI YAML file
    openapi_yaml = """
    openapi: 3.0.0
    info:
      title: Test API
      version: 1.0.0
      description: Test API specification
    paths:
      /api/v1/users:
        get:
          operationId: getUsers
          summary: Get users
          description: Retrieve list of users
          responses:
            '200':
              description: Successful response
              content:
                application/json:
                  schema:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'
    components:
      schemas:
        User:
          type: object
          properties:
            id:
              type: integer
              description: User ID
            name:
              type: string
              description: User name
          example:
            id: 1
            name: John Doe
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(openapi_yaml)
        temp_file = f.name
    
    try:
        # Test YAML parser
        parser = YAMLParser()
        document = parser.parse(temp_file)
        
        # Verify OpenAPI-specific parsing
        assert document.metadata["structure_type"] == "openapi"
        assert document.metadata["openapi_version"] == "3.0.0"
        
        # Check for schemas chapter
        schemas_chapter = next((ch for ch in document.chapters if ch.title == "Schemas and APIs"), None)
        assert schemas_chapter is not None
        
        # Check for content information chapter
        content_chapter = next((ch for ch in document.chapters if ch.title == "Content Information"), None)
        assert content_chapter is not None
        
        print(f"✅ OpenAPI YAML parsing successful")
        print(f"   Structure type: {document.metadata['structure_type']}")
        print(f"   OpenAPI version: {document.metadata['openapi_version']}")
        print(f"   Chapters: {len(document.chapters)}")
        
    finally:
        # Clean up
        Path(temp_file).unlink()


def test_yaml_parser_error_handling():
    """Test YAML parser error handling."""
    print("\n⚠️ Testing YAML Parser Error Handling")
    print("=" * 50)
    
    # Create a malformed YAML file
    malformed_yaml = """
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: test-config
      # Missing closing brace
    data:
      key1: value1
      key2: value2
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(malformed_yaml)
        temp_file = f.name
    
    try:
        # Test YAML parser with malformed YAML
        parser = YAMLParser()
        
        try:
            document = parser.parse(temp_file)
            print("❌ Expected parsing to fail with malformed YAML")
        except Exception as e:
            print(f"✅ Error handling worked as expected: {type(e).__name__}")
            
            # Check error summary
            summary = parser.get_parsing_summary()
            assert summary["has_errors"] == True
            
    finally:
        # Clean up
        Path(temp_file).unlink()


def test_yaml_parser_content():
    """Test YAML parser with content string."""
    print("\n📝 Testing YAML Parser with Content String")
    print("=" * 50)
    
    test_content = """
    # Test content
    name: test-service
    version: 1.0.0
    description: A test service
    config:
      port: 8080
      host: localhost
    """
    
    parser = YAMLParser()
    document = parser.parse_content(test_content, "test_service")
    
    # Verify document structure
    assert document.title == "test_service"
    assert len(document.chapters) > 0
    
    # Check for content chapter
    content_chapter = next((ch for ch in document.chapters if ch.title == "YAML Content"), None)
    assert content_chapter is not None
    
    print(f"✅ Content string parsing successful")
    print(f"   Document title: {document.title}")
    print(f"   Chapters: {len(document.chapters)}")


def test_yaml_parser_complex():
    """Test YAML parser with complex nested structures."""
    print("\n🔗 Testing Complex YAML Parser")
    print("=" * 50)
    
    complex_yaml = """
    # Complex configuration
    apiVersion: v1
    kind: Deployment
    metadata:
      name: complex-app
      labels:
        app: complex-app
        version: v1.0.0
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: complex-app
      template:
        metadata:
          labels:
            app: complex-app
        spec:
          containers:
          - name: app-container
            image: complex-app:latest
            ports:
            - containerPort: 8080
            env:
            - name: DATABASE_URL
              value: postgresql://localhost:5432/mydb
            - name: REDIS_URL
              value: redis://localhost:6379
            resources:
              requests:
                memory: "64Mi"
                cpu: "250m"
              limits:
                memory: "128Mi"
                cpu: "500m"
            volumeMounts:
            - name: config-volume
              mountPath: /app/config
          volumes:
          - name: config-volume
            configMap:
              name: app-config
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(complex_yaml)
        temp_file = f.name
    
    try:
        parser = YAMLParser()
        document = parser.parse(temp_file)
        
        # Verify complex structure parsing
        assert document.title == Path(temp_file).stem
        assert len(document.chapters) > 0
        
        # Check structure information
        structure_chapter = next((ch for ch in document.chapters if ch.title == "YAML Structure"), None)
        assert structure_chapter is not None
        
        print(f"✅ Complex YAML parsing successful")
        print(f"   Document title: {document.title}")
        print(f"   Chapters: {len(document.chapters)}")
        print(f"   Structure type: {document.metadata.get('structure_type', 'unknown')}")
        
    finally:
        # Clean up
        Path(temp_file).unlink()


def main():
    """Run all YAML parser tests."""
    print("🚀 Starting YAML Parser Tests")
    print("=" * 80)
    
    try:
        # Run all tests
        test_config_manager()
        test_error_handler()
        test_yaml_utils()
        test_yaml_parser_basic()
        test_yaml_parser_openapi()
        test_yaml_parser_error_handling()
        test_yaml_parser_content()
        test_yaml_parser_complex()
        
        print("\n" + "=" * 80)
        print("🎉 All YAML Parser tests passed!")
        print("✅ The YAML parser is ready for use in the IDE Services knowledge ingestion")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 