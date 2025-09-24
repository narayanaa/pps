#!/usr/bin/env python3
"""
Quick test to identify which imports are causing hangs
"""

import sys
import signal
from pathlib import Path

# Add parent directory to sys.path to ensure proper imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def timeout_handler(signum, frame):
    print(f"❌ Import hung at: {frame.f_code.co_filename}:{frame.f_lineno}")
    sys.exit(1)

# Set a 10-second timeout
signal.signal(signal.SIGALRM, timeout_handler)

print("🧪 Testing imports...")

try:
    signal.alarm(10)
    print("1. Testing scrapers module...")
    import scrapers
    print("✅ scrapers module imported")
    
    signal.alarm(10)
    print("2. Testing scrapers.psense module...")
    from scrapers import psense
    print("✅ scrapers.psense imported")
    
    signal.alarm(10) 
    print("3. Testing web scraper...")
    scraper_class = scrapers.WebScraper
    if scraper_class:
        print("✅ WebScraper class loaded successfully")
    else:
        print("❌ WebScraper is None")
    
    signal.alarm(10)
    print("4. Testing multilingual processor...")
    ml_class = scrapers.MultilingualProcessor
    if ml_class:
        print("✅ MultilingualProcessor loaded")
    else:
        print("⚠️ MultilingualProcessor is None")
        
    signal.alarm(10)
    print("5. Testing config manager...")
    config_class = scrapers.ConfigManager
    if config_class:
        print("✅ ConfigManager loaded")
    else:
        print("❌ ConfigManager is None")
        
    signal.alarm(0)  # Cancel alarm
    print("🎉 All imports successful!")

except Exception as e:
    signal.alarm(0)
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()