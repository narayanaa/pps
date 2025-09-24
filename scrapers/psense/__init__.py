"""
Psense Scrapers Module
Web scraping components for the unified document processing framework.
"""

# Lazy imports to avoid heavy dependencies during module loading
def __getattr__(name):
    if name == 'WebScraper':
        try:
            from .web.scraper import WebScraper
            return WebScraper
        except ImportError:
            try:
                from .web.standalone_scraper import StandaloneWebScraper
                return StandaloneWebScraper
            except ImportError:
                return None
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['WebScraper']