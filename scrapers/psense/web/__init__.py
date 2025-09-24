"""
Web Scraper Module for Psense Framework
Provides unified web scraping capabilities.
"""

# Lazy imports to avoid heavy dependencies during module loading
def _get_webscraper():
    try:
        from .scraper import WebScraper
        return WebScraper
    except ImportError:
        try:
            from .standalone_scraper import StandaloneWebScraper
            return StandaloneWebScraper
        except ImportError:
            return None

def _get_multilingual_processor():
    try:
        from .multilingual_processor import MultilingualProcessor
        return MultilingualProcessor
    except ImportError:
        return None

def _get_config_manager():
    try:
        from .run_scraper import ConfigManager
        return ConfigManager
    except ImportError:
        return None

# Lazy loading attributes
WebScraper = None
MultilingualProcessor = None
ConfigManager = None

def __getattr__(name):
    global WebScraper, MultilingualProcessor, ConfigManager
    
    if name == 'WebScraper' and WebScraper is None:
        WebScraper = _get_webscraper()
        return WebScraper
    elif name == 'MultilingualProcessor' and MultilingualProcessor is None:
        MultilingualProcessor = _get_multilingual_processor()
        return MultilingualProcessor
    elif name == 'ConfigManager' and ConfigManager is None:
        ConfigManager = _get_config_manager()
        return ConfigManager
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['WebScraper', 'MultilingualProcessor', 'ConfigManager']