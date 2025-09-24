#!/usr/bin/env python3
"""
Pre-Check-in Test Runner
Comprehensive test suite to validate the web scraper project before git commit
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_command(cmd, description, timeout=60):
    """Run a command and return success status"""
    print(f"\n🔍 {description}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent
        )
        
        if result.returncode == 0:
            print("✅ PASSED")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ FAILED")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT (>{timeout}s)")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return False

def test_basic_imports():
    """Test basic import functionality"""
    tests = [
        ("python -c 'from scrapers.psense.web.scraper import WebScraper; print(\"Main scraper import: OK\")'", 
         "Main Scraper Import"),
        ("python -c 'from scrapers.psense.web.multilingual_processor import MultilingualProcessor; print(\"Multilingual processor import: OK\")'", 
         "Multilingual Processor Import"),
        ("python -c 'import parsers.psense; print(\"Parsers import: OK\")'", 
         "Parsers Import"),
        ("python -c 'import doc.psense; print(\"Doc framework import: OK\")'", 
         "Doc Framework Import"),
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc, timeout=30))
    
    return all(results)

def test_individual_files():
    """Test individual test files"""
    test_files = [
        ("python tests/test_import.py", "Import Tests"),
        ("python tests/test_multilingual_integration.py", "Multilingual Integration Tests"),
        ("python tests/integration_test.py", "Integration Tests"),
    ]
    
    results = []
    for cmd, desc in test_files:
        results.append(run_command(cmd, desc, timeout=60))
    
    return all(results)

def test_parser_functionality():
    """Test parser functionality"""
    parser_tests = [
        ("python -c 'from parsers.psense.pdf.pdf_parser import PDFParser; print(\"PDF parser: OK\")'", 
         "PDF Parser"),
        ("python -c 'from parsers.psense.docx import DocxParser; print(\"DOCX parser: OK\")'", 
         "DOCX Parser"),
        ("python -c 'from parsers.psense.ebook import EpubParser; print(\"EPUB parser: OK\")'", 
         "EPUB Parser"),
    ]
    
    results = []
    for cmd, desc in parser_tests:
        results.append(run_command(cmd, desc, timeout=30))
    
    return all(results)

def test_scraper_basic_functionality():
    """Test scraper basic functionality with simple config"""
    print("\n🔍 Testing Scraper Basic Functionality")
    print("-" * 50)
    
    try:
        # Create minimal test
        test_script = '''
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from scrapers.psense.web.scraper import WebScraper

# Minimal config test
config = {
    "scraper": {
        "url": "https://httpbin.org/html",
        "max_depth": 0,
        "follow_links": False,
        "request_delay": 0.1,
        "connection_timeout": 10,
        "enable_multilingual": False
    }
}

try:
    scraper = WebScraper(config)
    print("✅ WebScraper initialization: OK")
    
    # Test basic methods
    stats = scraper.get_crawl_statistics()
    print("✅ Statistics method: OK")
    
    scraper.cleanup()
    print("✅ Cleanup method: OK")
    
    print("🎉 Basic scraper functionality: PASSED")
    
except Exception as e:
    print(f"❌ Scraper test failed: {e}")
    sys.exit(1)
'''
        
        with open("temp_scraper_test.py", "w") as f:
            f.write(test_script)
        
        result = run_command("python temp_scraper_test.py", "Scraper Basic Functionality", timeout=30)
        
        # Cleanup
        if os.path.exists("temp_scraper_test.py"):
            os.remove("temp_scraper_test.py")
        
        return result
        
    except Exception as e:
        print(f"💥 Test setup failed: {e}")
        return False

def test_config_loading():
    """Test configuration loading"""
    return run_command(
        "python -c 'import json; config=json.load(open(\"config.json\")); print(f\"Config loaded: {len(config)} sections\")'",
        "Configuration Loading",
        timeout=10
    )

def run_pytest_if_available():
    """Run pytest if available"""
    print("\n🔍 Running Pytest Suite (if available)")
    print("-" * 50)
    
    # Check if pytest is available
    try:
        result = subprocess.run(["python", "-m", "pytest", "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("⚠️  Pytest not available, skipping")
            return True
    except:
        print("⚠️  Pytest not available, skipping") 
        return True
    
    # Run pytest with timeout
    return run_command(
        "python -m pytest tests/ -v --tb=short --maxfail=3 -x",
        "Pytest Suite",
        timeout=120
    )

def main():
    """Main test runner"""
    print("🚀 PRE-CHECK-IN TEST SUITE")
    print("=" * 60)
    print("Running comprehensive tests before git commit...")
    
    start_time = time.time()
    
    # Test categories
    test_categories = [
        ("Basic Imports", test_basic_imports),
        ("Configuration", test_config_loading),
        ("Parser Functionality", test_parser_functionality),
        ("Scraper Functionality", test_scraper_basic_functionality),
        ("Individual Test Files", test_individual_files),
        ("Pytest Suite", run_pytest_if_available),
    ]
    
    results = {}
    
    for category_name, test_func in test_categories:
        print(f"\n📋 TESTING CATEGORY: {category_name}")
        print("=" * 60)
        
        try:
            success = test_func()
            results[category_name] = success
        except Exception as e:
            print(f"💥 Category failed with exception: {e}")
            results[category_name] = False
    
    # Summary
    elapsed = time.time() - start_time
    print(f"\n🎯 TEST RESULTS SUMMARY ({elapsed:.1f}s)")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for category, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {category:<25s}: {status}")
        if success:
            passed += 1
    
    print(f"\n📊 OVERALL: {passed}/{total} categories passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - READY FOR CHECK-IN!")
        print("✅ Your project is ready for git commit")
        return True
    else:
        print(f"\n⚠️  {total - passed} CATEGORIES FAILED")
        print("❌ Please fix issues before check-in")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)