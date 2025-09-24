#!/usr/bin/env python3
"""
Comprehensive Parser Validation Test Suite

This test validates that all parsers conform to the unified doc.psense structure
and can produce consistent, robust output.
"""

import sys
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph
from doc.psense.document.table import Table
from doc.psense.document.image import Image


class ParserValidationSuite:
    """Comprehensive validation suite for all document parsers"""
    
    def __init__(self):
        self.results = {
            "parsers_tested": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
    
    def validate_document_structure(self, doc: Document, parser_name: str) -> bool:
        """Validate that document conforms to unified structure"""
        try:
            # Test basic Document properties
            assert isinstance(doc, Document), f"{parser_name}: Must return Document instance"
            assert hasattr(doc, 'title'), f"{parser_name}: Document must have title"
            assert hasattr(doc, 'chapters'), f"{parser_name}: Document must have chapters"
            assert hasattr(doc, 'author'), f"{parser_name}: Document must have author"
            assert hasattr(doc, 'created_date'), f"{parser_name}: Document must have created_date"
            assert hasattr(doc, 'url'), f"{parser_name}: Document must have url"
            
            # Test required methods
            assert hasattr(doc, 'to_text'), f"{parser_name}: Document must have to_text method"
            assert hasattr(doc, 'to_dict'), f"{parser_name}: Document must have to_dict method"
            assert hasattr(doc, 'extract_metadata'), f"{parser_name}: Document must have extract_metadata method"
            assert hasattr(doc, 'get_entities'), f"{parser_name}: Document must have get_entities method"
            
            # Test chapters structure
            assert isinstance(doc.chapters, list), f"{parser_name}: chapters must be list"
            
            for i, chapter in enumerate(doc.chapters):
                assert isinstance(chapter, Chapter), f"{parser_name}: Chapter {i} must be Chapter instance"
                assert hasattr(chapter, 'title'), f"{parser_name}: Chapter {i} must have title"
                assert hasattr(chapter, 'sections'), f"{parser_name}: Chapter {i} must have sections"
                assert hasattr(chapter, 'number'), f"{parser_name}: Chapter {i} must have number"
                
                # Test chapter methods
                assert hasattr(chapter, 'to_dict'), f"{parser_name}: Chapter {i} must have to_dict method"
                assert hasattr(chapter, 'to_text'), f"{parser_name}: Chapter {i} must have to_text method"
                
                # Test sections
                assert isinstance(chapter.sections, list), f"{parser_name}: Chapter {i} sections must be list"
                
                for j, section in enumerate(chapter.sections):
                    assert isinstance(section, Section), f"{parser_name}: Section {j} must be Section instance"
                    assert hasattr(section, 'title'), f"{parser_name}: Section {j} must have title"
                    assert hasattr(section, 'content'), f"{parser_name}: Section {j} must have content"
                    assert hasattr(section, 'level'), f"{parser_name}: Section {j} must have level"
                    
                    # Test section methods
                    assert hasattr(section, 'to_dict'), f"{parser_name}: Section {j} must have to_dict method"
                    assert hasattr(section, 'to_text'), f"{parser_name}: Section {j} must have to_text method"
                    
                    # Test content
                    assert isinstance(section.content, list), f"{parser_name}: Section {j} content must be list"
                    
                    for k, content_item in enumerate(section.content):
                        # All content items must have these methods
                        assert hasattr(content_item, 'to_text'), f"{parser_name}: Content {k} must have to_text method"
                        assert hasattr(content_item, 'to_dict'), f"{parser_name}: Content {k} must have to_dict method"
                        assert hasattr(content_item, 'extract_metadata'), f"{parser_name}: Content {k} must have extract_metadata method"
                        assert hasattr(content_item, 'get_entities'), f"{parser_name}: Content {k} must have get_entities method"
                        
                        # Test specific content types
                        if isinstance(content_item, Paragraph):
                            assert hasattr(content_item, 'text'), f"{parser_name}: Paragraph {k} must have text"
                            assert hasattr(content_item, 'style'), f"{parser_name}: Paragraph {k} must have style"
                        elif isinstance(content_item, Table):
                            assert hasattr(content_item, 'data'), f"{parser_name}: Table {k} must have data"
                            assert hasattr(content_item, 'headers'), f"{parser_name}: Table {k} must have headers"
                            assert hasattr(content_item, 'caption'), f"{parser_name}: Table {k} must have caption"
                        elif isinstance(content_item, Image):
                            assert hasattr(content_item, 'file_path'), f"{parser_name}: Image {k} must have file_path"
                            assert hasattr(content_item, 'caption'), f"{parser_name}: Image {k} must have caption"
            
            return True
            
        except AssertionError as e:
            self.results["errors"].append(f"{parser_name}: {str(e)}")
            return False
        except Exception as e:
            self.results["errors"].append(f"{parser_name}: Unexpected error: {str(e)}")
            return False
    
    def test_serialization(self, doc: Document, parser_name: str) -> bool:
        """Test document serialization methods"""
        try:
            # Test to_text method
            text_output = doc.to_text()
            assert isinstance(text_output, str), f"{parser_name}: to_text must return string"
            assert len(text_output) > 0, f"{parser_name}: to_text must return non-empty string"
            
            # Test to_dict method
            dict_output = doc.to_dict()
            assert isinstance(dict_output, dict), f"{parser_name}: to_dict must return dict"
            assert 'title' in dict_output, f"{parser_name}: to_dict must include title"
            assert 'chapters' in dict_output, f"{parser_name}: to_dict must include chapters"
            
            # Test JSON serialization
            json_str = json.dumps(dict_output, default=str)
            assert len(json_str) > 0, f"{parser_name}: Document must be JSON serializable"
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"{parser_name}: Serialization error: {str(e)}")
            return False
    
    def test_metadata_extraction(self, doc: Document, parser_name: str) -> bool:
        """Test metadata extraction capabilities"""
        try:
            # Test basic metadata extraction
            metadata = doc.extract_metadata()
            assert isinstance(metadata, dict), f"{parser_name}: extract_metadata must return dict"
            
            # Test entities extraction
            entities = doc.get_entities()
            assert isinstance(entities, list), f"{parser_name}: get_entities must return list"
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"{parser_name}: Metadata extraction error: {str(e)}")
            return False
    
    def create_test_document(self) -> Document:
        """Create a test document for validation"""
        # Create test content
        paragraph = Paragraph("This is a test paragraph for validation.")
        table = Table(
            data=[["Name", "Value"], ["Test", "123"]], 
            headers=["Column1", "Column2"],
            caption="Test Table"
        )
        
        # Create test structure
        section = Section(
            title="Test Section",
            content=[paragraph, table],
            level=1
        )
        
        chapter = Chapter(
            title="Test Chapter",
            sections=[section],
            number=1
        )
        
        document = Document(
            title="Test Document",
            author="Test Author"
        )
        document.chapters = [chapter]
        
        return document
    
    def run_validation_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("🔍 Running Parser Validation Suite...")
        
        # Test 1: Basic document structure validation
        print("\n📋 Test 1: Document Structure Validation")
        test_doc = self.create_test_document()
        
        if self.validate_document_structure(test_doc, "TestDocument"):
            print("✅ Test document structure validation: PASSED")
            self.results["tests_passed"] += 1
        else:
            print("❌ Test document structure validation: FAILED")
            self.results["tests_failed"] += 1
        
        # Test 2: Serialization validation
        print("\n📤 Test 2: Serialization Validation")
        if self.test_serialization(test_doc, "TestDocument"):
            print("✅ Serialization validation: PASSED")
            self.results["tests_passed"] += 1
        else:
            print("❌ Serialization validation: FAILED")
            self.results["tests_failed"] += 1
        
        # Test 3: Metadata extraction validation
        print("\n📊 Test 3: Metadata Extraction Validation")
        if self.test_metadata_extraction(test_doc, "TestDocument"):
            print("✅ Metadata extraction validation: PASSED")
            self.results["tests_passed"] += 1
        else:
            print("❌ Metadata extraction validation: FAILED")
            self.results["tests_failed"] += 1
        
        # Test 4: Table interoperability
        print("\n📈 Test 4: Table Interoperability Validation")
        if self.test_table_interoperability():
            print("✅ Table interoperability: PASSED")
            self.results["tests_passed"] += 1
        else:
            print("❌ Table interoperability: FAILED")
            self.results["tests_failed"] += 1
        
        return self.results
    
    def test_table_interoperability(self) -> bool:
        """Test enhanced table interoperability features"""
        try:
            # Create test table
            table = Table(
                data=[["John", "25", "NYC"], ["Jane", "30", "LA"]],
                headers=["Name", "Age", "City"],
                caption="Test Table"
            )
            
            # Test enhanced to_dict
            table_dict = table.to_dict()
            assert "schema" in table_dict, "Table must have schema information"
            assert "data" in table_dict, "Table must have data section"
            assert "columns" in table_dict["data"], "Table must have column-oriented data"
            
            # Test DataFrame compatibility
            df_dict = table.to_dataframe_dict()
            assert isinstance(df_dict, dict), "to_dataframe_dict must return dict"
            assert "Name" in df_dict, "DataFrame dict must have Name column"
            
            # Test records format
            records = table.to_records()
            assert isinstance(records, list), "to_records must return list"
            assert len(records) == 2, "Records must have correct number of entries"
            
            # Test export formats
            csv_data = table.to_csv()
            html_data = table.to_html()
            excel_data = table.to_excel_data()
            
            assert isinstance(csv_data, str), "CSV export must return string"
            assert isinstance(html_data, str), "HTML export must return string"
            assert isinstance(excel_data, dict), "Excel export must return dict"
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"Table interoperability error: {str(e)}")
            return False
    
    def print_results(self):
        """Print validation results"""
        total_tests = self.results["tests_passed"] + self.results["tests_failed"]
        
        print(f"\n{'='*60}")
        print("📊 PARSER VALIDATION RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {self.results['tests_passed']}")
        print(f"❌ Failed: {self.results['tests_failed']}")
        
        if self.results["errors"]:
            print(f"\n🚨 ERRORS FOUND:")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        success_rate = (self.results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! Parsers are robust and conformant.")
        elif success_rate >= 80:
            print("⚠️  Most tests passed, but some issues need attention.")
        else:
            print("🚨 CRITICAL ISSUES FOUND - Immediate attention required.")


def main():
    """Main test runner"""
    validator = ParserValidationSuite()
    
    try:
        results = validator.run_validation_tests()
        validator.print_results()
        
        # Return appropriate exit code
        if results["tests_failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"🚨 CRITICAL ERROR in validation suite: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()