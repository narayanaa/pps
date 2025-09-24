#!/usr/bin/env python3
"""
Standalone Web Scraper - Zero Heavy Dependencies
This scraper is completely isolated from doc.psense and PDF parser dependencies.
It uses only lightweight libraries and internal classes.
"""

import os
import time
import logging
import json
import requests
import tempfile
import hashlib
import threading
from urllib.parse import urljoin, urlparse
from datetime import datetime
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import concurrent.futures

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# Lightweight document classes - completely independent
class StandaloneDocument:
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


class StandaloneChapter:
    def __init__(self, title: str, sections: List = None, number: int = 1):
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


class StandaloneSection:
    def __init__(self, title: str, content: List = None):
        self.title = title
        self.content = content or []
    
    def to_dict(self):
        return {
            "title": self.title,
            "content": [c.to_dict() if hasattr(c, 'to_dict') else str(c) for c in self.content]
        }


class StandaloneParagraph:
    def __init__(self, text: str):
        self.text = text
    
    def to_dict(self):
        return {"type": "paragraph", "text": self.text}


class StandaloneTable:
    def __init__(self, data: List = None, headers: List = None, caption: str = ""):
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


class StandaloneImage:
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


class StandaloneHyperlink:
    def __init__(self, url: str, text: str = ""):
        self.url = url
        self.text = text
    
    def to_dict(self):
        return {
            "type": "hyperlink",
            "url": self.url,
            "text": self.text
        }


class StandaloneWebScraper:
    """
    Standalone Web Scraper with zero heavy dependencies.
    Uses only requests, BeautifulSoup, and standard library.
    """

    def __init__(self, config: dict):
        s = config.get("scraper", {})
        self.base_url = s["url"]
        self.max_depth = s.get("max_depth", 2)
        self.follow_links = s.get("follow_links", False)
        self.request_delay = s.get("request_delay", 0.5)
        self.connection_timeout = s.get("connection_timeout", 10)
        self.retry_tries = s.get("retry_tries", 3)
        self.output_format = s.get("output_format", "json")
        self.output_path = s.get("output_path", "./standalone_output.json")
        self.verbose = s.get("verbose", True)
        self.concurrency = max(1, int(s.get("concurrency", 1)))
        
        # Simple settings
        self.allowed_domains = set(s.get("allowed_domains", []))
        self.ignore_file_exts = set(s.get("ignore_file_extensions", ["pdf", "doc", "docx", "zip", "exe"]))
        self.extract_tables = s.get("extract_tables", True)
        self.extract_images = s.get("extract_images", False)  # Disabled by default for simplicity
        
        # Noise filtering
        self.noise_keywords = s.get("noise_keywords", ["nav", "menu", "footer", "header", "sidebar", "cookie", "advert"])
        
        # Internal state
        self.visited = set()
        self.visited_lock = threading.Lock()
        self.failed_urls = []
        
        # Prepare network session with retries
        self.session = requests.Session()
        retries = Retry(
            total=self.retry_tries, 
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504], 
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Thread pool for concurrency
        if self.concurrency > 1:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency)
        else:
            self.executor = None
        
        logger.info(f"Standalone scraper initialized for {self.base_url}")

    def crawl(self) -> Optional[StandaloneDocument]:
        """Main crawl entry point"""
        try:
            logger.info("Starting standalone crawl at %s", self.base_url)
            root = self._crawl_recursive(self.base_url, 0)
            
            if self.failed_urls:
                logger.warning(f"Failed to fetch {len(self.failed_urls)} URLs during crawl")
            
            if root and self.output_path:
                self.save_output(root)
                
            return root
        except Exception as e:
            logger.exception("Crawl failed: %s", e)
            return None

    def _crawl_recursive(self, url: str, depth: int) -> Optional[StandaloneDocument]:
        """Core recursive crawler"""
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

        # Follow links if configured
        if self.follow_links and depth < self.max_depth:
            children = []
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"].split("#")[0])
                if self._is_valid_link(href):
                    children.append(href)

            if children:
                if self.executor:
                    # Concurrent crawling
                    futures = [self.executor.submit(self._crawl_recursive, href, depth + 1) for href in children]
                    for f in concurrent.futures.as_completed(futures):
                        try:
                            child_doc = f.result()
                            if child_doc:
                                doc.child_documents.append(child_doc)
                        except Exception as e:
                            logger.warning("Child crawl failed: %s", e)
                else:
                    # Sequential crawling
                    for href in children:
                        child = self._crawl_recursive(href, depth + 1)
                        if child:
                            doc.child_documents.append(child)

        return doc

    def safe_get(self, url: str) -> Optional[str]:
        """Fetch URL with error handling"""
        try:
            time.sleep(self.request_delay)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; StandaloneWebScraper/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            resp = self.session.get(url, headers=headers, timeout=self.connection_timeout)
            resp.raise_for_status()
            return resp.text
            
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            self.failed_urls.append(url)
            return None

    def _normalize_url(self, url: str) -> str:
        """Simple URL normalization"""
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path.rstrip('/')
            return f"{scheme}://{netloc}{path}"
        except Exception:
            return url

    def _is_valid_link(self, url: str) -> bool:
        """Check if URL should be crawled"""
        if not url:
            return False
        
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        if parsed.scheme in ("mailto", "javascript"):
            return False

        normalized_url = self._normalize_url(url)
        if normalized_url in self.visited:
            return False

        domain = parsed.netloc.lower()
        if self.allowed_domains and domain not in self.allowed_domains:
            if not any(domain.endswith(ad.lower()) for ad in self.allowed_domains):
                return False

        ext = os.path.splitext(parsed.path)[1].lstrip(".").lower()
        if ext and ext in self.ignore_file_exts:
            return False

        return True

    def is_noise(self, tag) -> bool:
        """Simple noise detection"""
        try:
            id_class = " ".join(filter(None, [*tag.get("class", []), tag.get("id", "")])).lower()
            if any(k in id_class for k in self.noise_keywords):
                return True
            txt = tag.get_text(strip=True)
            if not txt or len(txt) < 3:
                return True
            return False
        except Exception:
            return False

    def _parse_to_document(self, soup: BeautifulSoup, url: str) -> Optional[StandaloneDocument]:
        """Convert HTML to standalone document structure"""
        if soup is None:
            return None

        # Get title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        doc = StandaloneDocument(title=title, url=url, created_date=datetime.now())

        # Create root structure
        chapter = StandaloneChapter("Main", [], number=1)
        doc.add_chapter(chapter)
        section = StandaloneSection("Content", [])
        chapter.sections.append(section)

        # Process content
        for tag in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table", "img", "a"]):
            if self.is_noise(tag) or self._is_in_header_footer(tag):
                continue
            self._handle_tag(tag, chapter, section, doc)

        return doc

    def _is_in_header_footer(self, tag) -> bool:
        """Check if tag is in header/footer"""
        return bool(tag.find_parent(["header", "footer"]))

    def _handle_tag(self, tag, chapter, section, doc):
        """Process individual HTML tags"""
        text = tag.get_text(strip=True)
        name = tag.name.lower()

        if name == "h1":
            new_ch = StandaloneChapter(text or "Untitled", [], number=len(doc.chapters) + 1)
            doc.add_chapter(new_ch)
            ch_section = StandaloneSection(text or "Content", [])
            new_ch.sections.append(ch_section)
            return

        if name in ["h2", "h3"]:
            sec = StandaloneSection(text or "Untitled", [])
            chapter.sections.append(sec)
            return

        if name == "p" and text:
            section.content.append(StandaloneParagraph(text))
            return

        if name in ["ul", "ol"]:
            for li in tag.find_all("li"):
                if t := li.get_text(strip=True):
                    section.content.append(StandaloneParagraph(t))
            return

        if name == "table" and self.extract_tables:
            hdr, rows = self._extract_table(tag)
            section.content.append(StandaloneTable(data=rows, headers=hdr))
            return

        if name == "img" and self.extract_images:
            src = tag.get("src") or tag.get("data-src")
            if src:
                img_url = urljoin(self.base_url, src)
                alt = tag.get("alt", "")
                section.content.append(StandaloneImage(img_url, alt))
            return

        if name == "a":
            href = tag.get("href", "")
            txt = text or "[link]"
            section.content.append(StandaloneHyperlink(href, txt))
            return

    def _extract_table(self, tag):
        """Extract table data"""
        try:
            # Try using pandas first
            import pandas as pd
            from io import StringIO
            table_html = str(tag)
            df = pd.read_html(StringIO(table_html), header=0)[0]
            return list(df.columns), df.values.tolist()
        except Exception:
            # Fallback to manual extraction
            hdr, rows = [], []
            for i, tr in enumerate(tag.find_all("tr")):
                if i == 0:
                    hdr = [th.get_text(strip=True) for th in tr.find_all("th")]
                    if not hdr:  # No header row
                        hdr = [td.get_text(strip=True) for td in tr.find_all("td")]
                    else:
                        continue
                rows.append([td.get_text(strip=True) for td in tr.find_all("td")])
            return hdr, rows

    def save_output(self, document: StandaloneDocument):
        """Save document to file"""
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                if self.output_format == "json":
                    json.dump(document.to_dict(), f, indent=2, default=str)
                else:
                    f.write(document.to_text())
            logger.info(f"Output saved to {self.output_path}")
        except Exception as e:
            logger.error(f"Failed to save output: {e}")

    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get basic crawl statistics"""
        return {
            "total_urls_visited": len(self.visited),
            "total_failed_urls": len(self.failed_urls),
            "success_rate": (len(self.visited) - len(self.failed_urls)) / max(len(self.visited), 1) * 100,
        }

    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.executor:
                self.executor.shutdown(wait=False)
            if hasattr(self, 'session'):
                self.session.close()
            logger.info("Standalone scraper cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def main():
    """Test function"""
    config = {
        "scraper": {
            "url": "https://httpbin.org/html",
            "max_depth": 0,
            "follow_links": False,
            "request_delay": 0.5,
            "output_path": "standalone_test_output.json"
        }
    }
    
    with StandaloneWebScraper(config) as scraper:
        result = scraper.crawl()
        if result:
            stats = scraper.get_crawl_statistics()
            print("✅ Standalone scraper test successful!")
            print(f"Title: {result.title}")
            print(f"Chapters: {len(result.chapters)}")
            print(f"URLs processed: {stats['total_urls_visited']}")
        else:
            print("❌ Standalone scraper test failed")


if __name__ == "__main__":
    main()