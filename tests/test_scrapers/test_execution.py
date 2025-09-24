#!/usr/bin/env python3
"""
Test actual execution to find where hanging occurs
"""

import sys
import time

def test_step(step_name, test_func):
    """Test a step with timing"""
    print(f"Testing {step_name}...", end="", flush=True)
    start = time.time()
    try:
        result = test_func()
        elapsed = time.time() - start
        print(f" ✅ ({elapsed:.2f}s)")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f" ❌ ({elapsed:.2f}s): {e}")
        return None

def test_config_manager():
    from run_scraper import ConfigManager
    config_manager = ConfigManager("config.json")
    return config_manager

def test_config_build():
    from run_scraper import ConfigManager
    config_manager = ConfigManager("config.json")
    config = config_manager.build_config("https://httpbin.org/html", "quick")
    return config

def test_standalone_instantiation():
    from standalone_scraper import StandaloneWebScraper
    config = {'scraper': {'url': 'https://httpbin.org/html'}}
    scraper = StandaloneWebScraper(config)
    scraper.cleanup()
    return True

def test_original_instantiation():
    from scraper import WebScraper
    config = {'scraper': {'url': 'https://httpbin.org/html'}}
    scraper = WebScraper(config)
    scraper.cleanup()
    return True

def test_standalone_crawl():
    from standalone_scraper import StandaloneWebScraper
    config = {'scraper': {'url': 'https://httpbin.org/html'}}
    scraper = StandaloneWebScraper(config)
    result = scraper.crawl()
    scraper.cleanup()
    return result is not None

def test_original_crawl():
    from scraper import WebScraper
    config = {'scraper': {'url': 'https://httpbin.org/html'}}
    scraper = WebScraper(config)
    result = scraper.crawl()
    scraper.cleanup()
    return result is not None

def main():
    print("🔍 EXECUTION TEST")
    print("=" * 50)
    
    # Test config manager
    test_step("ConfigManager creation", test_config_manager)
    test_step("Config building", test_config_build)
    
    # Test instantiation
    test_step("Standalone instantiation", test_standalone_instantiation)
    test_step("Original instantiation", test_original_instantiation)
    
    # Test actual crawling
    test_step("Standalone crawl", test_standalone_crawl)
    test_step("Original crawl", test_original_crawl)
    
    print("=" * 50)
    print("Execution test completed!")

if __name__ == "__main__":
    main()