#!/usr/bin/env python3
"""
Test script to verify multilingual processor integration in main scraper
"""

import sys
import os
import json
import tempfile
from pathlib import Path

# Add the parent directory to Python path to access all modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_multilingual_integration():
    """Test the integration of multilingual processor with main scraper"""
    
    print("🧪 Testing Multilingual Processor Integration")
    print("=" * 50)
    
    try:
        # Import the enhanced scraper
        from scrapers.psense.web.scraper import WebScraper
        print("✅ Enhanced WebScraper imported successfully")
        
        # Test configuration with multilingual enabled
        config = {
            "scraper": {
                "url": "https://tax.gov.ae",
                "max_depth": 1,
                "follow_links": False,
                "enable_multilingual": True,
                "allowed_languages": ["en", "ar"],
                "request_delay": 0.1,
                "output_format": "json",
                "output_path": "/tmp/test_multilingual_output.json",
                "verbose": True
            },
            "language_support": {
                "supported_languages": {
                    "ar": {
                        "name": "Arabic",
                        "script": "arabic",
                        "encoding": "utf-8",
                        "url_patterns": ["/ar/", "/arabic/", "lang=ar"],
                        "content_selectors": ["[lang='ar']", "[dir='rtl']"]
                    },
                    "en": {
                        "name": "English", 
                        "script": "latin",
                        "encoding": "utf-8",
                        "url_patterns": ["/en/", "/english/", "lang=en"],
                        "content_selectors": ["[lang='en']", "[dir='ltr']"]
                    }
                },
                "language_detection": {
                    "confidence_threshold": 0.7,
                    "fallback_to_script": True
                },
                "text_processing": {
                    "normalize_unicode": True,
                    "rtl_support": True
                }
            }
        }
        
        # Initialize scraper
        scraper = WebScraper(config)
        print("✅ WebScraper initialized with multilingual configuration")
        
        # Check multilingual processor initialization
        if hasattr(scraper, 'multilingual_processor') and scraper.multilingual_processor:
            print("✅ Multilingual processor initialized successfully")
            
            # Test language detection
            test_texts = [
                "Welcome to the UAE Tax Authority website",
                "مرحباً بكم في موقع الهيئة الاتحادية للضرائب",
                "Tax registration process in the United Arab Emirates",
                "عملية التسجيل الضريبي في دولة الإمارات العربية المتحدة"
            ]
            
            print("\n🌐 Testing Language Detection:")
            for i, text in enumerate(test_texts, 1):
                lang_info = scraper.multilingual_processor.detect_language(text)
                print(f"  {i}. Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                print(f"     Language: {lang_info.name} ({lang_info.code})")
                print(f"     Script: {lang_info.script.value}, RTL: {lang_info.is_rtl}")
                print(f"     Confidence: {lang_info.confidence:.2f}")
                print()
        else:
            print("⚠️ Multilingual processor not available or not initialized")
        
        # Test document creation with fake HTML
        from bs4 import BeautifulSoup
        
        test_html = """
        <html>
        <head><title>UAE Tax Authority - الهيئة الاتحادية للضرائب</title></head>
        <body>
            <div lang="en">
                <h1>Welcome to UAE Tax Authority</h1>
                <p>The Federal Tax Authority (FTA) was established in accordance with Federal Law No. 13 of 2016.</p>
            </div>
            <div lang="ar" dir="rtl">
                <h1>مرحباً بكم في الهيئة الاتحادية للضرائب</h1>
                <p>تم إنشاء الهيئة الاتحادية للضرائب وفقاً للقانون الاتحادي رقم 13 لسنة 2016.</p>
            </div>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(test_html, 'html.parser')
        doc = scraper._parse_to_document(soup, "https://tax.gov.ae/test")
        
        if doc:
            print("✅ Document created successfully with multilingual content")
            
            # Check if multilingual metadata was added
            if hasattr(doc, 'cache') and 'multilingual_data' in doc.cache:
                multilingual_data = doc.cache['multilingual_data']
                print(f"  📊 Detected languages: {multilingual_data['detected_languages']}")
                print(f"  🌍 Primary language: {multilingual_data['primary_language']}")
                
                if multilingual_data['language_analysis']:
                    print("  📈 Language analysis:")
                    for lang, analysis in multilingual_data['language_analysis'].items():
                        print(f"    - {lang}: {analysis['text_count']} segments, {analysis['total_chars']} chars, direction: {analysis['direction']}")
            else:
                print("  ⚠️ No multilingual metadata found in document")
            
            # Test enhanced output format
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                scraper.output_path = tmp_file.name
                scraper.save_output(doc)
                
                # Read and verify the output
                with open(tmp_file.name, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                
                if 'multilingual_analysis' in output_data:
                    print("✅ Enhanced output format with multilingual analysis")
                    multilingual_analysis = output_data['multilingual_analysis']
                    print(f"  📋 Analysis includes: {list(multilingual_analysis.keys())}")
                else:
                    print("  ⚠️ No multilingual analysis in output")
                
                # Cleanup
                os.unlink(tmp_file.name)
        else:
            print("❌ Failed to create document")
        
        # Test crawl statistics
        stats = scraper.get_crawl_statistics()
        print("\n📊 Enhanced Crawl Statistics:")
        for key, value in stats.items():
            if key == 'multilingual_features':
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    - {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        print("\n🎉 Multilingual integration test completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_multilingual_integration()
    sys.exit(0 if success else 1)