#!/usr/bin/env python3
"""
Main Entry Point for Web Scraper with Multilingual Support

This script provides the main entry point that ensures:
1. All imports work correctly from the python directory
2. Config is loaded from the correct location (python/config.json)
3. The documentation examples work as expected

Usage:
    python run_scraper.py <url> [--profile PROFILE] [--config CONFIG_FILE] [--options KEY=VALUE ...]
    
Examples:
    python run_scraper.py https://tax.gov.ae/en/taxes/corporate.tax/faqs.aspx --profile tax_gov_ae
    python run_scraper.py https://example.com --profile quick
    python run_scraper.py https://example.com --profile balanced --options concurrency=20 request_delay=0.1
"""

import sys
import os
from pathlib import Path

# Ensure we're running from the correct directory and imports work
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import the actual runner from the scrapers module
try:
    from scrapers.psense.web.run_scraper import main as runner_main
    
    def main():
        # Override the default config path to use the top-level config.json
        import sys
        config_path = str(current_dir / "config.json")
        
        # If no --config argument is provided, inject the correct config path
        if '--config' not in sys.argv and '-c' not in sys.argv:
            # Find the position to insert config argument
            # Insert after the URL but before other options
            insert_pos = 2 if len(sys.argv) > 1 else 1
            sys.argv.insert(insert_pos, '--config')
            sys.argv.insert(insert_pos + 1, config_path)
        
        # Call the actual main function
        runner_main()
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"📍 Current directory: {current_dir}")
    print(f"📍 Python path: {sys.path[:3]}...")
    print("💡 Make sure you're running from /Users/narayana.rallabandi/DevCode/web_scraper/python/")
    print("💡 Check that all required files are present in the scrapers/psense/web/ directory")
    sys.exit(1)

