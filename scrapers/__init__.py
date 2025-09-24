"""
Web Scraper Module for Psense Framework
Provides unified web scraping capabilities.
"""

# Import submodules to make them accessible
try:
    from . import psense
except ImportError:
    psense = None

# Lazy imports to prevent heavy dependency loading
def __getattr__(name):
    if name == 'WebScraper':
        try:
            from .psense.web.scraper import WebScraper
            return WebScraper
        except ImportError:
            try:
                from .psense.web.standalone_scraper import StandaloneWebScraper
                return StandaloneWebScraper
            except ImportError:
                return None
    elif name == 'MultilingualProcessor':
        try:
            from .psense.web.multilingual_processor import MultilingualProcessor
            return MultilingualProcessor
        except ImportError:
            return None
    elif name == 'ConfigManager':
        try:
            from .psense.web.run_scraper import ConfigManager
            return ConfigManager
        except ImportError:
            return None
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['WebScraper', 'MultilingualProcessor', 'ConfigManager', 'psense']
