#!/usr/bin/env python3
"""
Minimal test to isolate the exact cause of hanging
"""

import sys
import time

def test_step(step_name, test_func):
    """Test a step with timing"""
    print(f"Testing {step_name}...", end="", flush=True)
    start = time.time()
    try:
        test_func()
        elapsed = time.time() - start
        print(f" ✅ ({elapsed:.2f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f" ❌ ({elapsed:.2f}s): {e}")
        return False

def test_basic_imports():
    import os, json, time, logging

def test_requests():
    import requests

def test_bs4():
    from bs4 import BeautifulSoup

def test_pandas():
    import pandas

def test_config_load():
    import json
    with open('config.json', 'r') as f:
        config = json.load(f)
    return len(config)

def test_standalone_import():
    from standalone_scraper import StandaloneWebScraper

def test_original_scraper_import():
    from scraper import WebScraper

def main():
    print("🔍 SYSTEMATIC ISOLATION TEST")
    print("=" * 50)
    
    # Test basic imports
    test_step("Basic imports", test_basic_imports)
    test_step("Requests", test_requests) 
    test_step("BeautifulSoup", test_bs4)
    test_step("Pandas", test_pandas)
    
    # Test config loading
    test_step("Config.json loading", test_config_load)
    
    # Test scraper imports
    test_step("Standalone scraper import", test_standalone_import)
    test_step("Original scraper import", test_original_scraper_import)
    
    print("=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    main()