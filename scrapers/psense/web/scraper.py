from __future__ import annotations

# domain_pipeline/core/scraper_enhanced.py
"""
Enhanced, modular WebScraper based on the uploaded scraper.py.
- Preserves all public/private method signatures (no signature changes).
- Adds a configurable network layer (requests.Session with retries)
- Optional concurrent crawling via ThreadPoolExecutor (configurable)
- Simple on-disk caching (optional)
- Optional robots.txt respect
- Improved logging and error handling
- Graceful optional JS rendering if Playwright is available
- Image handling with optional SVG conversion if cairosvg is present
- Duplicate detection via Simhash (configurable similarity threshold)
"""


import os
import time
import logging
import tempfile
import requests
import backoff
import pandas as pd
import json
import random
import threading
import hashlib
import mimetypes
import asyncio
import xml.etree.ElementTree as ET
from collections import defaultdict
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from io import BytesIO
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
import sqlite3
import pickle
from pathlib import Path
from typing import TYPE_CHECKING
from aiohttp import ClientSession


from bs4 import BeautifulSoup, Comment
from simhash import Simhash
from PIL import Image as PILImage, UnidentifiedImageError

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures

# Set up logging first
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Added for enhancement A: Async fetcher
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

# Added for enhancement: Language detection
try:
    import langdetect
    LANGDETECT_AVAILABLE = True
except ImportError:
    langdetect = None
    LANGDETECT_AVAILABLE = False

# Added for enhancement: Progress monitoring
try:
    import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    tqdm = None
    TQDM_AVAILABLE = False

# document model imports - import from the python directory structure
try:
    import sys
    from pathlib import Path
    
    # Get the absolute path to the python directory (3 levels up from this file)
    current_file = Path(__file__).resolve()
    python_dir = current_file.parent.parent.parent.parent
    
    if str(python_dir) not in sys.path:
        sys.path.insert(0, str(python_dir))
    
    from doc.psense.document.document import Document
    from doc.psense.document.chapter import Chapter
    from doc.psense.document.section import Section
    from doc.psense.document.paragraph import Paragraph
    from doc.psense.document.table import Table
    from doc.psense.document.image import Image
    from doc.psense.document.hyperlink import Hyperlink
    DOC_FRAMEWORK_AVAILABLE = True
    logger.info("✅ Successfully imported full doc.psense framework")
except ImportError as e:
    logger.warning(f"⚠️ Could not import doc.psense framework: {e}")
    logger.warning("Creating lightweight fallback classes...")
    DOC_FRAMEWORK_AVAILABLE = False
    
    # Minimal fallback classes
    class Document:
        def __init__(self, title: str = "", url: str = "", created_date: Optional[datetime] = None):
            self.title = title
            self.url = url
            self.created_date = created_date or datetime.now()
            self.chapters = []
            self.child_documents = []
        
        def add_chapter(self, chapter):
            self.chapters.append(chapter)
        
        def to_dict(self):
            return {
                "title": self.title,
                "url": self.url,
                "created_date": self.created_date.isoformat(),
                "chapters": [ch.to_dict() if hasattr(ch, 'to_dict') else str(ch) for ch in self.chapters],
                "child_documents": [doc.to_dict() if hasattr(doc, 'to_dict') else str(doc) for doc in self.child_documents]
            }
        
        def to_text(self):
            lines = [f"Document: {self.title}"]
            for chapter in self.chapters:
                if hasattr(chapter, 'to_text'):
                    lines.append(chapter.to_text())
                else:
                    lines.append(str(chapter))
            return "\n".join(lines)

    class Chapter:
        def __init__(self, title: str, sections = None, number: int = 1):
            self.title = title
            self.sections = sections or []
            self.number = number
        
        def to_dict(self):
            return {
                "title": self.title,
                "number": self.number,
                "sections": [sec.to_dict() if hasattr(sec, 'to_dict') else str(sec) for sec in self.sections]
            }
        
        def to_text(self):
            return f"Chapter {self.number}: {self.title}"

    class Section:
        def __init__(self, title: str, content = None):
            self.title = title
            self.content = content or []
        
        def to_dict(self):
            return {
                "title": self.title,
                "content": [c.to_dict() if hasattr(c, 'to_dict') else str(c) for c in self.content]
            }

    class Paragraph:
        def __init__(self, text: str):
            self.text = text
        
        def to_dict(self):
            return {"type": "paragraph", "text": self.text}

    class Table:
        def __init__(self, data = None, headers = None, caption: str = ""):
            self.data = data or []
            self.headers = headers or []
            self.caption = caption
        
        def to_dict(self):
            return {
                "type": "table",
                "data": self.data,
                "headers": self.headers,
                "caption": self.caption
            }

    class Image:
        def __init__(self, src: str, alt: str = "", caption: str = ""):
            self.src = src
            self.alt = alt
            self.caption = caption
        
        def to_dict(self):
            return {
                "type": "image",
                "src": self.src,
                "alt": self.alt,
                "caption": self.caption
            }

    class Hyperlink:
        def __init__(self, url: str, text: str = ""):
            self.url = url
            self.text = text
        
        def to_dict(self):
            return {
                "type": "hyperlink",
                "url": self.url,
                "text": self.text
            }

# optional utilities
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:
    cairosvg = None
    CAIROSVG_AVAILABLE = False

try:
    from urllib import robotparser as robotparser_module
    ROBOTPARSER_AVAILABLE = True
except Exception:
    ROBOTPARSER_AVAILABLE = False

# Multilingual processor import
try:
    from .multilingual_processor import MultilingualProcessor
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MultilingualProcessor = None
    MULTILINGUAL_AVAILABLE = False

if TYPE_CHECKING:
    import aiohttp


# Phase 1: Infrastructure - Circuit Breaker Pattern
class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = requests.exceptions.RequestException


class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient network operations"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self.lock:
                if self.state == CircuitBreakerState.OPEN:
                    if self._should_attempt_reset():
                        self.state = CircuitBreakerState.HALF_OPEN
                    else:
                        raise Exception("Circuit breaker is OPEN")
                
                try:
                    result = func(*args, **kwargs)
                    self._on_success()
                    return result
                except self.config.expected_exception as e:
                    self._on_failure()
                    raise e
        return wrapper
    
    def _should_attempt_reset(self):
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.config.recovery_timeout
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN


# Phase 2: Content Intelligence - Advanced Content Classification
class ContentType(Enum):
    ARTICLE = "article"
    PRODUCT = "product"
    NEWS = "news"
    BLOG = "blog"
    FORUM = "forum"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class ContentClassifier:
    """AI-powered content classification system"""
    
    def __init__(self):
        self.patterns = {
            ContentType.ARTICLE: ["article", "post", "content", "main"],
            ContentType.PRODUCT: ["product", "item", "price", "buy", "cart"],
            ContentType.NEWS: ["news", "breaking", "headline", "reporter"],
            ContentType.BLOG: ["blog", "author", "comment", "tag"],
            ContentType.FORUM: ["forum", "thread", "reply", "member"],
            ContentType.DOCUMENTATION: ["docs", "api", "reference", "guide"]
        }
    
    def classify_content(self, soup: BeautifulSoup, url: str) -> ContentType:
        """Classify content based on structure and text patterns"""
        text = soup.get_text().lower()
        classes = " ".join([tag.get("class", []) for tag in soup.find_all() if tag.get("class")])
        
        scores = {content_type: 0 for content_type in ContentType}
        
        for content_type, keywords in self.patterns.items():
            for keyword in keywords:
                scores[content_type] += text.count(keyword) + classes.count(keyword)
        
        # URL-based classification
        url_lower = url.lower()
        if "/blog/" in url_lower or "/article/" in url_lower:
            scores[ContentType.BLOG] += 10
        elif "/product/" in url_lower or "/item/" in url_lower:
            scores[ContentType.PRODUCT] += 10
        elif "/news/" in url_lower:
            scores[ContentType.NEWS] += 10
        
        max_score_type = max(scores.keys(), key=lambda x: scores[x])
        return max_score_type if scores[max_score_type] > 0 else ContentType.UNKNOWN


# Phase 3: Database Integration for Scalability
class DatabaseManager:
    """SQLite-based persistence layer for crawl data"""
    
    def __init__(self, db_path: str = "scraper_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS crawl_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    config TEXT
                );
                
                CREATE TABLE IF NOT EXISTS crawled_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    url TEXT,
                    content_type TEXT,
                    status_code INTEGER,
                    content_hash TEXT,
                    crawl_time TIMESTAMP,
                    response_size INTEGER,
                    FOREIGN KEY (session_id) REFERENCES crawl_sessions(session_id)
                );
                
                CREATE TABLE IF NOT EXISTS failed_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    url TEXT,
                    error_message TEXT,
                    attempt_count INTEGER,
                    last_attempt TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES crawl_sessions(session_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_url_hash ON crawled_urls(content_hash);
                CREATE INDEX IF NOT EXISTS idx_session_url ON crawled_urls(session_id, url);
            """)
    
    def start_session(self, session_id: str, config: dict):
        """Start a new crawl session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO crawl_sessions (session_id, start_time, config) VALUES (?, ?, ?)",
                (session_id, datetime.now(), json.dumps(config))
            )
    
    def end_session(self, session_id: str):
        """End a crawl session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE crawl_sessions SET end_time = ? WHERE session_id = ?",
                (datetime.now(), session_id)
            )
    
    def log_crawled_url(self, session_id: str, url: str, content_type: str, 
                       status_code: int, content_hash: str, response_size: int):
        """Log a successfully crawled URL"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO crawled_urls 
                   (session_id, url, content_type, status_code, content_hash, crawl_time, response_size)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, url, content_type, status_code, content_hash, datetime.now(), response_size)
            )
    
    def log_failed_url(self, session_id: str, url: str, error_message: str, attempt_count: int):
        """Log a failed URL attempt"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO failed_urls 
                   (session_id, url, error_message, attempt_count, last_attempt)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, url, error_message, attempt_count, datetime.now())
            )
    
    def is_url_crawled(self, url: str, content_hash: Optional[str] = None) -> bool:
        """Check if URL was already crawled"""
        with sqlite3.connect(self.db_path) as conn:
            if content_hash:
                result = conn.execute(
                    "SELECT 1 FROM crawled_urls WHERE url = ? OR content_hash = ?",
                    (url, content_hash)
                ).fetchone()
            else:
                result = conn.execute(
                    "SELECT 1 FROM crawled_urls WHERE url = ?",
                    (url,)
                ).fetchone()
            return result is not None


class WebScraper:
    """
    Enhanced WebScraper. Method signatures are preserved so you can drop-in replace the original
    implementation. Internally the class is more modular and configurable.

    Config (example keys under config['scraper']):
      - url (required)
      - max_depth (int)
      - follow_links (bool)
      - request_delay (float) seconds between requests
      - dynamic_rendering (bool) (try Playwright if available)
      - allowed_domains (list)
      - allowed_languages (list)  # not enforced by default - placeholder
      - ignore_file_extensions (list)
      - extract_tables (bool)
      - extract_images (bool)
      - ocr_images (bool)
      - convert_svg (bool)
      - connection_timeout (float) (requests timeout)
      - retry_tries (int)
      - retry_backoff_seconds (float)
      - output_format (json|text)
      - output_path (str)
      - noise_keywords (list)
      - verbose (bool)
      - concurrency (int) number of threads for crawling
      - cache_dir (str) if provided will cache HTML responses
      - cache_ttl (int) seconds TTL for cache files
      - respect_robots (bool)
      - user_agents (list) optional user-agent rotation
    """

    def __init__(self, config: dict):
        s = config.get("scraper", {})
        self.base_url = s["url"]
        self.max_depth = s.get("max_depth", 2)
        self.follow_links = s.get("follow_links", False)
        self.request_delay = s.get("request_delay", 0.1)
        self.dynamic_rendering = s.get("dynamic_rendering", False)

        self.allowed_domains = set(s.get("allowed_domains", []))
        self.allowed_languages = s.get("allowed_languages", [])
        self.ignore_file_exts = set(s.get("ignore_file_extensions", []))

        self.extract_tables = s.get("extract_tables", True)
        self.extract_images = s.get("extract_images", True)
        self.ocr_images = s.get("ocr_images", True)
        self.convert_svg = s.get("convert_svg", True)

        self.connection_timeout = s.get("connection_timeout", 10)
        self.retry_tries = s.get("retry_tries", 3)
        self.retry_backoff_seconds = s.get("retry_backoff_seconds", 2)

        self.output_format = s.get("output_format", "json")
        self.output_path = s.get("output_path", "./output.json")

        self.noise_keywords = s.get("noise_keywords", ["nav", "menu", "footer", "header", "sidebar", "cookie", "advert"])
        self.verbose = s.get("verbose", True)

        self.concurrency = max(1, int(s.get("concurrency", 1)))
        self.cache_dir = s.get("cache_dir", None)
        self.cache_ttl = s.get("cache_ttl", 24 * 3600)
        self.respect_robots = s.get("respect_robots", False)
        self.user_agents = s.get("user_agents", [])

        # Added for enhancement B: Proxy rotation
        self.proxies = s.get("proxies", [])
        self.proxy_lock = threading.Lock()  # Thread-safe proxy rotation

        # Added for enhancement C: Domain-aware rate limiting
        self.per_domain_max = s.get("per_domain_max", 2)
        self.domain_semaphores = defaultdict(lambda: threading.Semaphore(self.per_domain_max))

        # Added for enhancement: Language detection
        self.allowed_languages = s.get("allowed_languages", [])

        # Phase 1: Infrastructure - Circuit Breaker Configuration
        self.enable_circuit_breaker = s.get("enable_circuit_breaker", True)
        circuit_config = CircuitBreakerConfig(
            failure_threshold=s.get("circuit_breaker_threshold", 5),
            recovery_timeout=s.get("circuit_breaker_timeout", 60),
            expected_exception=requests.exceptions.RequestException
        )
        self.circuit_breaker = CircuitBreaker(circuit_config) if self.enable_circuit_breaker else None

        # Phase 2: Content Intelligence
        self.enable_content_classification = s.get("enable_content_classification", True)
        self.content_classifier = ContentClassifier() if self.enable_content_classification else None

        # Phase 3: Database Integration
        self.enable_database = s.get("enable_database", False)
        self.db_manager = DatabaseManager(s.get("database_path", "scraper_data.db")) if self.enable_database else None
        self.session_id = s.get("session_id", f"session_{int(time.time())}")

        # Advanced retry configuration
        self.max_retry_attempts = s.get("max_retry_attempts", 3)
        self.retry_delay_base = s.get("retry_delay_base", 1.0)
        self.retry_delay_max = s.get("retry_delay_max", 60.0)

        # Duplicate detection settings
        self.min_text_len = s.get("min_text_len", 30)
        self.similarity_threshold = s.get("similarity_threshold", 3)

        # internal state
        self.visited = set()
        self.simhashes = set()
        self.visited_lock = threading.Lock()
        self.simhash_lock = threading.Lock()
        
        # Added for enhancement: Failed URLs tracking
        self.failed_urls = []
        self.failed_urls_lock = threading.Lock()

        # Prepare network session with retries
        self.session = requests.Session()
        retries = Retry(total=self.retry_tries, backoff_factor=self.retry_backoff_seconds,
                        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "POST"])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Thread pool used for concurrency (kept alive for recursive submissions)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency)

        # simple cache folder if requested
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)

        # robots.txt and sitemap support
        self._robots = None
        self.sitemap_urls = set()  # Added for enhancement: Sitemap support
        if self.respect_robots and ROBOTPARSER_AVAILABLE:
            try:
                rp = robotparser_module.RobotFileParser()
                parsed = urlparse(self.base_url)
                robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
                rp.set_url(robots_url)
                rp.read()
                self._robots = rp
                # Added for enhancement: Parse sitemaps from robots.txt
                self._parse_sitemaps_from_robots(robots_url)
            except Exception as e:
                logger.warning("Failed to parse robots.txt: %s", e)
                self._robots = None

        if log_file := s.get("log_file"):
            fh = logging.FileHandler(log_file)
            fh.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(fh)
        
        # Initialize database session if enabled
        if self.enable_database and self.db_manager:
            self.db_manager.start_session(self.session_id, config)

        # Initialize multilingual processor if available
        self.multilingual_processor = None
        self.enable_multilingual = s.get("enable_multilingual", False)
        if self.enable_multilingual and MULTILINGUAL_AVAILABLE:
            try:
                self.multilingual_processor = MultilingualProcessor(config)
                logger.info("✅ Multilingual processor initialized")
            except Exception as e:
                logger.warning(f"⚠️ Multilingual processor initialization failed: {e}")
                self.enable_multilingual = False
        elif self.enable_multilingual:
            logger.warning("⚠️ Multilingual processing requested but not available")

    # -------------------- Networking helpers --------------------
    def _make_headers(self, extra: Optional[dict] = None) -> dict:
        # Enhanced for enhancement B: Better user-agent rotation
        headers = {
            "User-Agent": random.choice(self.user_agents) if self.user_agents else "Mozilla/5.0 (compatible; WebScraper/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if extra:
            headers.update(extra)
        return headers

    def _get_proxy(self) -> Optional[dict]:
        """Added for enhancement B: Thread-safe proxy rotation"""
        if not self.proxies:
            return None
        with self.proxy_lock:
            proxy = random.choice(self.proxies)
            return {"http": proxy, "https": proxy}

    def _normalize_url(self, url: str) -> str:
        """Added for enhancement: URL normalization to avoid duplicates"""
        try:
            parsed = urlparse(url)
            # Lowercase scheme and netloc
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            # Remove fragment and trailing slash from path
            path = parsed.path.rstrip('/')
            # Sort query parameters
            query_params = parse_qs(parsed.query)
            sorted_query = urlencode(sorted(query_params.items()))
            
            normalized = f"{scheme}://{netloc}{path}"
            if sorted_query:
                normalized += f"?{sorted_query}"
            return normalized
        except Exception:
            return url

    def _parse_sitemaps_from_robots(self, robots_url: str):
        """Added for enhancement: Sitemap support from robots.txt"""
        try:
            resp = self.session.get(robots_url, timeout=self.connection_timeout)
            if resp.status_code == 200:
                for line in resp.text.split('\n'):
                    if line.strip().lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        self._parse_sitemap(sitemap_url)
        except Exception as e:
            logger.debug(f"Failed to parse sitemaps from robots.txt: {e}")

    def _parse_sitemap(self, sitemap_url: str):
        """Added for enhancement: Parse XML sitemap"""
        try:
            resp = self.session.get(sitemap_url, timeout=self.connection_timeout)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                # Handle sitemap index
                for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        self._parse_sitemap(loc.text)
                # Handle URL entries
                for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc is not None:
                        self.sitemap_urls.add(self._normalize_url(loc.text))
        except Exception as e:
            logger.debug(f"Failed to parse sitemap {sitemap_url}: {e}")

    def _cache_path_for_url(self, url: str) -> str:
        if not self.cache_dir:
            return ""
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{key}.cache")

    def _read_cache(self, url: str) -> Optional[str]:
        if not self.cache_dir:
            return None
        p = self._cache_path_for_url(url)
        if not os.path.exists(p):
            return None
        age = time.time() - os.path.getmtime(p)
        if age > self.cache_ttl:
            return None
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    def _write_cache(self, url: str, content: str):
        if not self.cache_dir:
            return
        p = self._cache_path_for_url(url)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

    def _is_allowed_by_robots(self, url: str) -> bool:
        if not self.respect_robots or self._robots is None:
            return True
        try:
            return self._robots.can_fetch(self._make_headers().get("User-Agent"), url)
        except Exception:
            return True

    # Added for enhancement A: Async fetcher methods
    async def _fetch_async(self, url: str, session: 'ClientSession') -> Optional[str]:
        """Added for enhancement A: Async single URL fetch with aiohttp"""
        if not AIOHTTP_AVAILABLE:
            return None
            
        # Check cache first
        if cached := self._read_cache(url):
            logger.debug("Cache hit (async): %s", url)
            return cached

        if not self._is_allowed_by_robots(url):
            logger.info("Blocked by robots.txt (async): %s", url)
            return None

        headers = self._make_headers()
        proxy = self._get_proxy()
        
        try:
            async with session.get(url, headers=headers, proxy=proxy, timeout=self.connection_timeout) as resp:
                resp.raise_for_status()
                content = await resp.text()
                self._write_cache(url, content)
                return content
        except Exception as e:
            logger.warning(f"Async fetch failed for {url}: {e}")
            with self.failed_urls_lock:
                self.failed_urls.append(url)
            return None

    async def _fetch_async_batch(self, urls: List[str]) -> List[Optional[str]]:
        """Added for enhancement A: Async batch fetcher for API/XHR endpoints"""
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp not available, cannot use async batch fetch")
            return [None] * len(urls)
            
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit_per_host=self.per_domain_max),
            timeout=aiohttp.ClientTimeout(total=self.connection_timeout)
        ) as session:
            tasks = []
            for url in urls:
                # Apply domain-aware rate limiting with semaphore
                domain = urlparse(url).netloc
                # For async, we'll use a simpler approach and rely on connector limits
                tasks.append(self._fetch_async(url, session))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to None
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append(None)
                else:
                    processed_results.append(result)
            
            return processed_results

    def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Enhanced fetch with exponential backoff retry and circuit breaker"""
        for attempt in range(self.max_retry_attempts):
            try:
                if self.enable_circuit_breaker and self.circuit_breaker:
                    return self.circuit_breaker(self._fetch_internal)(url)
                else:
                    return self._fetch_internal(url)
            except Exception as e:
                if attempt == self.max_retry_attempts - 1:
                    # Log failed attempt to database
                    if self.enable_database and self.db_manager:
                        self.db_manager.log_failed_url(self.session_id, url, str(e), attempt + 1)
                    raise
                
                # Exponential backoff with jitter
                delay = min(
                    self.retry_delay_base * (2 ** attempt) + random.uniform(0, 1),
                    self.retry_delay_max
                )
                logger.warning(f"Attempt {attempt + 1} failed for {url}, retrying in {delay:.2f}s: {e}")
                time.sleep(delay)
        
        return None

    def _fetch_internal(self, url: str) -> Optional[str]:
        """
        Low level fetch. Synchronous by design (keeps original signature). Will try Playwright rendering
        if dynamic_rendering==True and Playwright is available. Uses requests.Session (retries configured).
        """
        # cache
        if cached := self._read_cache(url):
            logger.debug("Cache hit: %s", url)
            return cached

        if not self._is_allowed_by_robots(url):
            logger.info("Blocked by robots.txt: %s", url)
            return None

        headers = self._make_headers()
        # Added for enhancement B: Proxy rotation
        proxy = self._get_proxy()
        proxies = proxy if proxy else None
        
        try:
            if self.dynamic_rendering:
                # try to use Playwright if available
                try:
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch(headless=True)
                        page = browser.new_page()
                        page.set_extra_http_headers(headers)
                        page.goto(url, timeout=int(self.connection_timeout * 1000))
                        content = page.content()
                        browser.close()
                        self._write_cache(url, content)
                        return content
                except Exception as e:
                    logger.debug("Playwright rendering not available or failed (%s), falling back to requests", e)

            resp = self.session.get(url, headers=headers, proxies=proxies, timeout=self.connection_timeout)
            resp.raise_for_status()
            text = resp.text
            self._write_cache(url, text)
            
            # Log successful crawl to database
            if self.enable_database and self.db_manager:
                content_hash = hashlib.md5(text.encode()).hexdigest()
                content_type = "unknown"
                if self.enable_content_classification and self.content_classifier:
                    soup = BeautifulSoup(text, "lxml")
                    content_type = self.content_classifier.classify_content(soup, url).value
                
                self.db_manager.log_crawled_url(
                    self.session_id, url, content_type, resp.status_code, 
                    content_hash, len(text)
                )
            
            return text
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch %s : %s", url, e)
            # Added for enhancement: Track failed URLs
            with self.failed_urls_lock:
                self.failed_urls.append(url)
            raise

    # high-level wrapper that applies rate limiting and exception handling
    def safe_get(self, url: str) -> Optional[str]:
        """
        Public wrapper (signature preserved). Uses backoff-decorated _fetch and enforces request_delay.
        Returns HTML text or None.
        Enhanced with domain-aware rate limiting.
        """
        # Added for enhancement C: Domain-aware rate limiting
        domain = urlparse(url).netloc
        semaphore = self.domain_semaphores[domain]
        
        try:
            with semaphore:  # Acquire domain semaphore
                time.sleep(self.request_delay)
                html = self._fetch_with_retry(url)
                return html
        except Exception as e:
            logger.warning("safe_get failed for %s: %s", url, e)
            return None

    # -------------------- Crawl logic --------------------
    def crawl(self) -> Optional[Document]:
        """
        Entry point to start crawling. Preserves signature.
        Enhanced with failed URLs reporting.
        """
        try:
            logger.info("Starting crawl at %s", self.base_url)
            root = self._crawl_recursive(self.base_url, 0)
            
            # Added for enhancement: Report failed URLs at the end
            if self.failed_urls:
                logger.warning(f"Failed to fetch {len(self.failed_urls)} URLs during crawl:")
                for url in self.failed_urls[:10]:  # Show first 10
                    logger.warning(f"  - {url}")
                if len(self.failed_urls) > 10:
                    logger.warning(f"  ... and {len(self.failed_urls) - 10} more")
            
            if root and self.output_path:
                self.save_output(root)
            
            # End database session if enabled
            if self.enable_database and self.db_manager:
                self.db_manager.end_session(self.session_id)
                
            return root
        except Exception as e:
            logger.exception("Crawl failed: %s", e)
            # End database session on error
            if self.enable_database and self.db_manager:
                self.db_manager.end_session(self.session_id)
            return None

    def _crawl_recursive(self, url: str, depth: int) -> Optional[Document]:
        """
        Core recursive crawler. Preserves signature.
        Uses a thread pool for sibling pages when concurrency > 1.
        Enhanced with URL normalization and sitemap integration.
        """
        # Added for enhancement: URL normalization
        normalized_url = self._normalize_url(url)
        
        with self.visited_lock:
            if normalized_url in self.visited:
                logger.debug("Already visited %s", normalized_url)
                return None
            self.visited.add(normalized_url)

        html = self.safe_get(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        doc = self._parse_to_document(soup, url)
        if doc is None:
            return None

        # optionally follow links
        if self.follow_links and depth < self.max_depth:
            children = []
            # Regular links
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"].split("#")[0])
                if self._is_valid_link(href):
                    children.append(href)
            
            # Added for enhancement: Include sitemap URLs if we're at root level
            if depth == 0 and self.sitemap_urls:
                for sitemap_url in list(self.sitemap_urls)[:50]:  # Limit to prevent overload
                    if self._is_valid_link(sitemap_url):
                        children.append(sitemap_url)

            if children:
                # Added for enhancement: Progress monitoring with tqdm
                if TQDM_AVAILABLE and depth == 0:
                    children_iter = tqdm.tqdm(children, desc=f"Crawling depth {depth+1}")
                else:
                    children_iter = children
                    
                if self.concurrency > 1:
                    futures = [self.executor.submit(self._crawl_recursive, href, depth + 1) for href in children]
                    
                    if TQDM_AVAILABLE and depth == 0:
                        futures_iter = tqdm.tqdm(concurrent.futures.as_completed(futures), 
                                               total=len(futures), desc="Processing pages")
                    else:
                        futures_iter = concurrent.futures.as_completed(futures)
                        
                    for f in futures_iter:
                        try:
                            child_doc = f.result()
                        except Exception as e:
                            logger.warning("Child crawl failed: %s", e)
                            child_doc = None
                        if child_doc:
                            doc.child_documents.append(child_doc)
                else:
                    for href in children_iter:
                        child = self._crawl_recursive(href, depth + 1)
                        if child:
                            doc.child_documents.append(child)

        return doc

    def _is_valid_link(self, url: str) -> bool:
        # basic checks: scheme, visited, domain, extension
        if not url:
            return False
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        # avoid fragments, mailto, javascript etc.
        if parsed.scheme in ("mailto", "javascript"):
            return False

        # Added for enhancement: Use normalized URL for checks
        normalized_url = self._normalize_url(url)
        if normalized_url in self.visited:
            return False
        
        # Database-based deduplication check
        if self.enable_database and self.db_manager:
            if self.db_manager.is_url_crawled(normalized_url):
                logger.debug(f"URL already crawled in previous session: {normalized_url}")
                return False

        domain = parsed.netloc.lower()
        if self.allowed_domains and domain not in self.allowed_domains:
            # allow subdomains if they end with the allowed domain
            if not any(domain.endswith(ad.lower()) for ad in self.allowed_domains):
                return False

        # ignore file extensions
        ext = os.path.splitext(parsed.path)[1].lstrip(".").lower()
        if ext and ext in self.ignore_file_exts:
            return False

        # robots check
        if not self._is_allowed_by_robots(url):
            return False

        return True

    # -------------------- Duplication & Noise --------------------
    def _is_duplicate(self, html: str) -> bool:
        """
        Compute a simhash on the visible text and compare with previous hashes.
        Thread-safe.
        """
        if not html:
            return False
        soup = BeautifulSoup(html, "lxml")
        for s in soup(["script", "style"]):
            s.extract()
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for c in comments:
            c.extract()
        text = soup.get_text(separator=" ", strip=True)
        if len(text) < self.min_text_len:
            return True  # treat tiny pages as duplicate/noise to avoid processing

        new_hash = Simhash(text).value
        with self.simhash_lock:
            for old in self.simhashes:
                # use Hamming distance
                if bin(new_hash ^ old).count("1") < self.similarity_threshold:
                    logger.debug("Detected duplicate page by simhash")
                    return True
            self.simhashes.add(new_hash)
        return False

    def is_noise(self, tag) -> bool:
        """
        Heuristic noise detection based on id/class attributes and tag name.
        """
        try:
            id_class = " ".join(filter(None, [*tag.get("class", []), tag.get("id", "")])).lower()
            if any(k in id_class for k in self.noise_keywords):
                return True
            # very small tags
            txt = tag.get_text(strip=True)
            if not txt or len(txt) < 3:
                return True
            return False
        except Exception:
            return False

    # -------------------- Parsing --------------------
    def _parse_to_document(self, soup: BeautifulSoup, url: str) -> Optional[Document]:
        """
        Convert BeautifulSoup object into Document (using Document/Chapter/Section classes).
        Now includes multilingual processing and enhanced language metadata.
        Preserves signature. Enhanced with language detection.
        """
        if soup is None:
            return None

        if self._is_duplicate(str(soup)):
            logger.info("Skipping duplicate/short page: %s", url)
            return None

        # Enhanced multilingual processing
        multilingual_content = None
        detected_languages = []
        primary_language = "en"  # Default
        
        if self.enable_multilingual and self.multilingual_processor:
            try:
                # Extract multilingual content from HTML
                html_content = str(soup)
                multilingual_content = self.multilingual_processor.extract_multilingual_content(html_content, soup)
                
                if multilingual_content:
                    detected_languages = list(multilingual_content.keys())
                    # Primary language is the one with most content
                    primary_language = max(multilingual_content.keys(), 
                                         key=lambda lang: len(' '.join(multilingual_content[lang]['texts'])))
                    
                    logger.info(f"🌐 Detected languages: {detected_languages} (primary: {primary_language})")
                else:
                    # Fallback to simple text detection
                    main_text = soup.get_text(strip=True)[:1000]
                    if main_text:
                        lang_info = self.multilingual_processor.detect_language(main_text)
                        primary_language = lang_info.code
                        detected_languages = [primary_language]
                        logger.info(f"🌐 Detected language: {primary_language} (confidence: {lang_info.confidence:.2f})")
            except Exception as e:
                logger.debug(f"Multilingual processing failed for {url}: {e}")

        # Legacy language detection if multilingual processor not available
        elif self.allowed_languages and LANGDETECT_AVAILABLE:
            try:
                text = soup.get_text(strip=True)[:1000]  # Sample first 1000 chars
                if text:
                    detected_lang = langdetect.detect(text)
                    if detected_lang not in self.allowed_languages:
                        logger.info(f"Skipping page due to language {detected_lang}: {url}")
                        return None
                    primary_language = detected_lang
                    detected_languages = [detected_lang]
            except Exception as e:
                logger.debug(f"Language detection failed for {url}: {e}")

        # title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        doc = Document(title=title, url=url, created_date=datetime.now())
        
        # Add multilingual metadata to document (store in a custom attribute)
        if hasattr(doc, '__dict__'):  # Ensure we can add custom attributes
            doc.multilingual_data = {
                'detected_languages': detected_languages,
                'primary_language': primary_language,
                'multilingual_content': multilingual_content,
                'language_analysis': {
                    lang: {
                        'direction': content.get('direction', 'ltr'),
                        'script': content.get('script', 'latin'),
                        'text_count': len(content.get('texts', [])),
                        'total_chars': sum(len(text) for text in content.get('texts', []))
                    } for lang, content in (multilingual_content or {}).items()
                }
            }

        # start root chapter/section
        chapter = Chapter("Main", [], number=1)
        doc.add_chapter(chapter)
        section = Section("Content", [])
        chapter.sections.append(section)

        for tag in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table", "img", "a"]):
            if self.is_noise(tag) or self._is_in_header_footer(tag):
                continue
            self._handle_tag(tag, chapter, section, doc)

        return doc

    def _is_in_header_footer(self, tag) -> bool:
        return bool(tag.find_parent(["header", "footer"]))

    def _handle_tag(self, tag, chapter: Chapter, section: Section, doc: Document):
        text = tag.get_text(strip=True)
        name = tag.name.lower()

        if name == "h1":
            new_ch = Chapter(text or "Untitled", [], number=len(doc.chapters) + 1)
            doc.add_chapter(new_ch)
            # start new section inside new chapter
            ch_section = Section(text or "Content", [])
            new_ch.sections.append(ch_section)
            return

        # update section pointer for h2/h3
        if name in ["h2", "h3"]:
            sec = Section(text or "Untitled", [])
            chapter.sections.append(sec)
            return

        if name == "p" and text:
            section.content.append(Paragraph(text))
            return

        if name in ["ul", "ol"]:
            for li in tag.find_all("li"):
                if t := li.get_text(strip=True):
                    section.content.append(Paragraph(t))
            return

        if name == "table" and self.extract_tables:
            hdr, rows = self._extract_table(tag)
            section.content.append(Table(data=rows, headers=hdr))
            return

        if name == "img" and self.extract_images:
            self._process_image(tag, chapter, section, doc)
            return

        if name == "a":
            href = tag.get("href", "")
            txt = text or "[link]"
            ext = href.lower().split(".")[-1] if href else ""
            if ext in self.ignore_file_exts:
                section.content.append(Paragraph(f"{ext.upper()} link: {href}"))
            else:
                section.content.append(Hyperlink(href, txt))
            return

    def _extract_table(self, tag) -> Tuple[List[str], List[List[str]]]:
        """
        Returns headers, rows
        """
        try:
            df = pd.read_html(str(tag), header=0)[0]
            return list(df.columns), df.values.tolist()
        except Exception:
            hdr, rows = [], []
            for i, tr in enumerate(tag.find_all("tr")):
                if i == 0:
                    hdr = [th.get_text(strip=True) for th in tr.find_all("th")]
                else:
                    rows.append([td.get_text(strip=True) for td in tr.find_all("td")])
            return hdr, rows

    def _process_image(self, tag, chapter: Chapter, section: Section, document: Document):
        """
        Download and (optionally) convert images. Create Image document objects.
        """
        src = tag.get("src") or tag.get("data-src") or tag.get("data-original")
        if not src:
            return
        url = urljoin(self.base_url, src)
        if not urlparse(url).netloc:
            return
        try:
            resp = self.session.get(url, timeout=self.connection_timeout)
            resp.raise_for_status()
            data = resp.content

            # convert SVG to PNG optionally
            if self.convert_svg and url.lower().endswith(".svg") and CAIROSVG_AVAILABLE:
                try:
                    png_bytes = cairosvg.svg2png(bytestring=data)
                    data = png_bytes
                except Exception as e:
                    logger.debug("SVG conversion failed: %s", e)

            pil = PILImage.open(BytesIO(data))
            ext = (pil.format or "PNG").lower()
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            pil.save(tmp.name)
            tmp.close()

            img_obj = Image(tmp.name, caption=tag.get("alt", "").strip())
            # If Image object exposes OCR capabilities, keep them (implementation-dependent)
            if self.ocr_images and getattr(img_obj, "ocr_data", None):
                if isinstance(img_obj.ocr_data, list):
                    img_obj.ocr_data = {"ocr_text": " ".join(sum(img_obj.ocr_data, []))}
            if getattr(img_obj, "ocr_data", None):
                section.content.append(img_obj)
            else:
                # append at least a reference for non-ocr images
                section.content.append(img_obj)
        except (requests.RequestException, UnidentifiedImageError, Exception) as e:
            logger.warning(f"Image processing failed for {url}: {e}")

    # -------------------- Output --------------------
    def save_output(self, document: Document):
        """
        Keep signature; write JSON or plain text depending on config.
        Enhanced with multilingual metadata in output.
        """
        with open(self.output_path, "w", encoding="utf-8") as f:
            if self.output_format == "json":
                doc_dict = document.to_dict()
                
                # Add enhanced multilingual metadata to output
                if hasattr(document, 'multilingual_data'):
                    multilingual_data = document.multilingual_data
                    doc_dict['multilingual_analysis'] = {
                        'detected_languages': multilingual_data.get('detected_languages', []),
                        'primary_language': multilingual_data.get('primary_language', 'en'),
                        'language_analysis': multilingual_data.get('language_analysis', {}),
                        'content_by_language': {
                            lang: {
                                'text_samples': content['texts'][:3] if content.get('texts') else [],  # First 3 text samples
                                'direction': content.get('direction', 'ltr'),
                                'script': content.get('script', 'latin'),
                                'total_segments': len(content.get('texts', []))
                            } for lang, content in (multilingual_data.get('multilingual_content') or {}).items()
                        }
                    }
                
                f.write(json.dumps(doc_dict, indent=2, default=str, ensure_ascii=False))
            else:
                f.write(self.print_content(document))
        
        logger.info(f"Output saved to {self.output_path}")

    def print_content(self, document: Document) -> str:
        """
        Flatten the Document object to structured text for saving or inspection.
        """
        return document.to_text()
    
    # Phase 4: Analytics and Reporting Methods
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get comprehensive crawl statistics with multilingual insights"""
        stats = {
            "total_urls_visited": len(self.visited),
            "total_failed_urls": len(self.failed_urls),
            "success_rate": (len(self.visited) - len(self.failed_urls)) / max(len(self.visited), 1) * 100,
            "session_id": self.session_id if hasattr(self, 'session_id') else None,
            "multilingual_enabled": self.enable_multilingual if hasattr(self, 'enable_multilingual') else False,
        }
        
        # Add multilingual processing statistics
        if hasattr(self, 'enable_multilingual') and self.enable_multilingual:
            stats["multilingual_features"] = {
                "processor_available": MULTILINGUAL_AVAILABLE,
                "processor_initialized": self.multilingual_processor is not None,
                "supported_languages": list(self.multilingual_processor.supported_languages.keys()) if self.multilingual_processor else [],
                "detection_methods": ["unicode_script_analysis", "langdetect", "url_pattern_matching", "html_lang_attributes"]
            }
        
        if self.enable_database and self.db_manager:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                # Content type distribution
                result = conn.execute(
                    "SELECT content_type, COUNT(*) FROM crawled_urls WHERE session_id = ? GROUP BY content_type",
                    (self.session_id,)
                ).fetchall()
                stats["content_type_distribution"] = dict(result)
                
                # Total response size
                result = conn.execute(
                    "SELECT SUM(response_size) FROM crawled_urls WHERE session_id = ?",
                    (self.session_id,)
                ).fetchone()
                stats["total_response_size"] = result[0] if result[0] else 0
        
        return stats
    
    def cleanup(self):
        """Cleanup resources and close connections"""
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=True)
        
        if self.enable_database and self.db_manager:
            # Ensure session is properly ended
            try:
                self.db_manager.end_session(self.session_id)
            except Exception:
                pass  # Session might already be ended
        
        logger.info("WebScraper cleanup completed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()
