#!/usr/bin/env python3
"""
Configuration-driven Web Scraper Runner
Supports multiple profiles and domain-specific optimizations.

Usage:
    python run_scraper.py <url> [--profile PROFILE] [--config CONFIG_FILE] [--options KEY=VALUE ...]
    
Examples:
    python run_scraper.py https://tax.gov.ae/en/taxes/corporate.tax/faqs.aspx --profile tax_gov_ae
    python run_scraper.py https://example.com --profile quick
    python run_scraper.py https://example.com --profile balanced --options concurrency=20 request_delay=0.1
"""

import sys, io

# Ensure stdout/stderr are usable in constrained environments (e.g., test runners)
try:
    if getattr(sys.stdout, "closed", False):
        sys.stdout = sys.__stdout__
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    sys.stdout = sys.__stdout__

try:
    if getattr(sys.stderr, "closed", False):
        sys.stderr = sys.__stderr__
except Exception:
    sys.stderr = sys.__stderr__

import logging

# File handler
file_handler = logging.FileHandler("scraper.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)   # keep full logs in file
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Show INFO and above in console
console_handler.setFormatter(logging.Formatter("%(message)s"))

# Root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)



import sys
import json
import argparse
import time
from typing import Dict, Any, Optional
from pathlib import Path
# Import scraper with safe fallback - try standalone first to avoid hangs
try:
    from scrapers.psense.web.standalone_scraper import StandaloneWebScraper as WebScraper
    print("ℹ️  Using standalone scraper (lightweight, fast)")
except ImportError as e:
    print(f"⚠️  Could not import standalone scraper: {e}")
    try:
        from scrapers.psense.web.scraper import WebScraper
        print("ℹ️  Using sophisticated scraper (full-featured)")
    except ImportError:
        print("❌ Could not import any scraper")
        sys.exit(1)

# Enable multilingual support with lazy loading
MULTILINGUAL_AVAILABLE = True
MultilingualProcessor = None

def get_multilingual_processor():
    """Lazy load multilingual processor to avoid heavy imports during module loading"""
    global MultilingualProcessor
    if MultilingualProcessor is None:
        try:
            from scrapers.psense.web.multilingual_processor import MultilingualProcessor as MP
            MultilingualProcessor = MP
            return MultilingualProcessor
        except ImportError as e:
            print(f"⚠️  Multilingual processor not available: {e}")
            global MULTILINGUAL_AVAILABLE
            MULTILINGUAL_AVAILABLE = False
            return None
    return MultilingualProcessor


class ConfigManager:
    """Manages configuration profiles and merging"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                 return json.load(f)
        except FileNotFoundError:
            print(f"❌ Configuration file {self.config_file} not found")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {self.config_file}: {e}")
            sys.exit(1)
    
    def get_available_profiles(self) -> list:
        """Get list of available profiles"""
        return list(self.config.get("profiles", {}).keys())
    
    def build_config(self, url: str, profile: Optional[str] = None, custom_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build final configuration by merging base config, profile, and custom options"""
        
        # Start with base scraper config
        final_config = {"scraper": self.config["scraper"].copy()}
        
        # Set the target URL
        final_config["scraper"]["url"] = url
        
        # Apply profile if specified
        if profile:
            if profile not in self.config.get("profiles", {}):
                available = ", ".join(self.get_available_profiles())
                print(f"❌ Unknown profile '{profile}'. Available profiles: {available}")
                sys.exit(1)
            
            profile_config = self.config["profiles"][profile]
            # Remove description fields before merging
            profile_clean = {k: v for k, v in profile_config.items() if not k.startswith("_")}
            final_config["scraper"].update(profile_clean)
        
        # Apply domain-specific optimizations
        self._apply_domain_optimizations(final_config, url)
        
        # Apply custom options
        if custom_options:
            final_config["scraper"].update(custom_options)
        
        # Generate session ID with profile info
        import time
        timestamp = int(time.time())
        profile_suffix = f"_{profile}" if profile else ""
        final_config["scraper"]["session_id"] = f"session_{timestamp}{profile_suffix}"
        
        # Set output path with profile info
        if profile and "output_path" in final_config["scraper"]:
            base_path = final_config["scraper"]["output_path"]
            name, ext = base_path.rsplit(".", 1) if "." in base_path else (base_path, "json")
            final_config["scraper"]["output_path"] = f"{name}_{profile}.{ext}"
        
        return final_config
    
    def _apply_domain_optimizations(self, config: Dict[str, Any], url: str):
        """Apply domain-specific optimizations based on URL patterns"""
        domain_configs = self.config.get("domain_specific", {})
        
        # Detect language from URL if multilingual processor is available
        detected_languages = []
        if MULTILINGUAL_AVAILABLE:
            processor_class = get_multilingual_processor()
            if processor_class is not None:
                try:
                    processor = processor_class(self.config)
                    # Check URL patterns for language detection
                    for lang_code, lang_config in self.config.get("language_support", {}).get("supported_languages", {}).items():
                        url_patterns = lang_config.get("url_patterns", [])
                        if any(pattern in url.lower() for pattern in url_patterns):
                            detected_languages.append(lang_code)
                            print(f"🌐 Detected language from URL: {lang_config.get('name', lang_code)}")
                    
                    # If multilingual content detected, enable multilingual processing
                    if detected_languages:
                        config["scraper"]["enable_multilingual"] = True
                        config["scraper"]["detected_languages"] = detected_languages
                except Exception as e:
                    print(f"⚠️  Language detection failed: {e}")
        
        for domain_type, domain_config in domain_configs.items():
            if domain_type.startswith("_"):  # Skip description fields
                continue
                
            patterns = domain_config.get("patterns", [])
            if any(pattern in url.lower() for pattern in patterns):
                print(f"🎯 Applying {domain_type} optimizations")
                # Apply domain-specific settings
                domain_settings = {k: v for k, v in domain_config.items() 
                                 if k not in ["patterns", "exclude_patterns"]}
                config["scraper"].update(domain_settings)
                
                # Apply URL filtering
                exclude_patterns = domain_config.get("exclude_patterns", [])
                if exclude_patterns:
                    current_exts = config["scraper"].get("ignore_file_extensions", [])
                    # Add patterns as extensions to ignore (simplified approach)
                    config["scraper"]["ignore_file_extensions"] = list(set(current_exts + exclude_patterns))
                break
    
    def print_profile_info(self, profile: str):
        """Print information about a specific profile"""
        if profile not in self.config.get("profiles", {}):
            print(f"❌ Unknown profile '{profile}'")
            return
            
        profile_config = self.config["profiles"][profile]
        print(f"📋 Profile: {profile}")
        print(f"   Description: {profile_config.get('_description', 'No description')}")
        print(f"   Use Case: {profile_config.get('_use_case', 'General purpose')}")
        print(f"   Estimated Time: {profile_config.get('_estimated_time', 'Variable')}")
        print()


def parse_custom_options(options_list: list) -> Dict[str, Any]:
    """Parse custom options from command line arguments"""
    options = {}
    for option in options_list:
        if "=" not in option:
            print(f"❌ Invalid option format: {option}. Use KEY=VALUE")
            continue
            
        key, value = option.split("=", 1)
        
        # Try to parse as appropriate type
        if value.lower() in ["true", "false"]:
            options[key] = value.lower() == "true"
        elif value.isdigit():
            options[key] = int(value)
        else:
            try:
                options[key] = float(value)
            except ValueError:
                options[key] = value
    
    return options


def print_performance_summary(scraper: WebScraper, start_time: float, profile: Optional[str] = None):
    """Print comprehensive performance summary"""
    duration = time.time() - start_time
    pages_found = len(scraper.visited) if hasattr(scraper, 'visited') else 0
    
    print("\n" + "="*60)
    print("📊 CRAWL PERFORMANCE SUMMARY")
    print("="*60)
    
    if profile:
        print(f"🏷️  Profile Used: {profile}")
    
    print(f"⏱️  Total Duration: {duration:.1f} seconds")
    print(f"📄 Pages Processed: {pages_found}")
    
    if duration > 0:
        speed = pages_found / duration
        print(f"🚀 Average Speed: {speed:.1f} pages/second")
        
        # Performance categorization
        if speed > 5:
            print("🟢 Performance: Excellent")
        elif speed > 2:
            print("🟡 Performance: Good")
        elif speed > 0.5:
            print("🟠 Performance: Moderate")
        else:
            print("🔴 Performance: Slow - Consider optimizing")
    
    # Get detailed statistics if available
    if hasattr(scraper, 'get_crawl_statistics'):
        stats = scraper.get_crawl_statistics()
        print(f"📈 Success Rate: {stats.get('success_rate', 0):.1f}%")
        print(f"❌ Failed URLs: {stats.get('total_failed_urls', 0)}")
        
        if stats.get('total_response_size'):
            size_mb = stats['total_response_size'] / (1024 * 1024)
            print(f"💾 Data Retrieved: {size_mb:.1f} MB")
        
        content_dist = stats.get('content_type_distribution', {})
        if content_dist:
            print("📑 Content Types:")
            for content_type, count in content_dist.items():
                print(f"   - {content_type}: {count}")
    
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Configuration-driven Web Scraper with Multiple Profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick assessment of a site
  python run_scraper.py https://example.com --profile quick
  
  # Optimized crawl for UAE Tax Authority
  python run_scraper.py https://tax.gov.ae/en/taxes/corporate.tax/faqs.aspx --profile tax_gov_ae
  
  # Balanced crawl with custom concurrency
  python run_scraper.py https://example.com --profile balanced --options concurrency=20
  
  # Custom configuration with multiple options
  python run_scraper.py https://example.com --options max_depth=3 request_delay=0.1 concurrency=15
        """
    )
    
    parser.add_argument("url", nargs="?", help="Target URL to scrape")
    parser.add_argument("--profile", "-p", help="Configuration profile to use")
    parser.add_argument("--config", "-c", default="config.json", help="Configuration file path")
    parser.add_argument("--options", "-o", nargs="*", default=[], help="Custom options (KEY=VALUE)")
    parser.add_argument("--list-profiles", action="store_true", help="List available profiles and exit")
    parser.add_argument("--show-profile", help="Show details of a specific profile")
    parser.add_argument("--dry-run", action="store_true", help="Show configuration without running scraper")
    
    args = parser.parse_args()
    
    # Initialize configuration manager
    config_manager = ConfigManager(args.config)
    
    # Handle special commands
    if args.list_profiles:
        profiles = config_manager.get_available_profiles()
        print("🔧 Available Profiles:")
        print("=" * 30)
        for profile in profiles:
            config_manager.print_profile_info(profile)
        return
    
    if args.show_profile:
        config_manager.print_profile_info(args.show_profile)
        return
    
    # Validate URL is provided for scraping operations
    if not args.url:
        print("❌ URL is required for scraping operations")
        parser.print_help()
        sys.exit(1)
    
    # Parse custom options
    custom_options = parse_custom_options(args.options)
    
    # Build configuration
    try:
        config = config_manager.build_config(args.url, args.profile, custom_options)
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    # Print configuration summary
    print("🚀 WEB SCRAPER CONFIGURATION")
    print("=" * 40)
    print(f"🌐 Target URL: {args.url}")
    if args.profile:
        config_manager.print_profile_info(args.profile)
    
    scraper_config = config["scraper"]
    print(f"🔧 Configuration:")
    print(f"   Max Depth: {scraper_config.get('max_depth', 'unlimited')}")
    print(f"   Concurrency: {scraper_config.get('concurrency', 1)}")
    print(f"   Request Delay: {scraper_config.get('request_delay', 0)}s")
    print(f"   Follow Links: {scraper_config.get('follow_links', False)}")
    print(f"   Database Enabled: {scraper_config.get('enable_database', False)}")
    print(f"   Content Classification: {scraper_config.get('enable_content_classification', False)}")
    print(f"   Multilingual Support: {scraper_config.get('enable_multilingual', False)}")
    
    # Show detected languages if any
    detected_languages = scraper_config.get('detected_languages', [])
    if detected_languages:
        print(f"   Detected Languages: {', '.join(detected_languages)}")
    
    print(f"   Output: {scraper_config.get('output_path', 'console')}")
    
    if custom_options:
        print(f"⚙️  Custom Options: {custom_options}")
    
    if args.dry_run:
        print("\n🏁 Dry run completed - configuration shown above")
        return
    
    print("\n🚀 Starting crawl...")
    start_time = time.time()
    scraper = None
    
    try:
        # Initialize and run scraper
        scraper = WebScraper(config)
        result = scraper.crawl()
        
        if result:
            print("✅ Crawl completed successfully!")
            print_performance_summary(scraper, start_time, args.profile)
        else:
            print("❌ Crawl failed or returned no results")
            
    except KeyboardInterrupt:
        print("\n⚠️  Crawl interrupted by user")
    except Exception as e:
        print(f"❌ Crawl failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup if scraper was created
        if scraper is not None:
            scraper.cleanup()


if __name__ == "__main__":
    main()