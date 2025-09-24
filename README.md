# Unified Unstructured Data Framework

This repository provides a unified document model and processing pipeline for unstructured data across Web, PDF, DOCX, EPUB, and Markdown. It separates concerns into three layers:

- `doc/`: canonical, format-agnostic document classes (the unified model)
- `scrapers/`: web scraping to populate the model from HTML/websites
- `parsers/`: file-format parsers to populate the model from PDFs/DOCX/EPUB/MD/YAML

The goal is consistent interpretation of content regardless of source, enabling downstream analytics, search, and knowledge systems.

## 📁 Repository Layout
```
/doc/                      # Unified document model (Document, Chapter, Section, Paragraph, Table, Image, ...)
/scrapers/psense/web/      # Web scraper engine, profiles, CLI runner
/parsers/psense/           # Parsers for PDF, DOCX, EPUB, MD, YAML (+ tests)
requirements.txt           # Runtime dependencies across scrapers/parsers/model
```

Key modules:
- `doc/psense/document/*`: core classes, metadata, hyperlinks, images, tables, glossary, appendix, ToC
- `scrapers/psense/web/scraper.py`: scraping engine; `run_scraper.py` CLI; `config.json` profiles
- `parsers/psense/pdf/*`: staged PDF pipeline (layout, OCR, segmentation, metadata, entities, citations, tables)
- `parsers/psense/docx/docx_parser.py`: DOCX → unified model
- `parsers/psense/ebook/epub_parser.py`: EPUB → unified model
- `parsers/psense/md/md_parser.py`: Markdown → unified model
- `parsers/psense/yaml/yaml_parser.py`: YAML → unified model

## 🚀 Quick Start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional: spaCy model for NLP features
python -m spacy download en_core_web_sm
```

### Run the Web Scraper
```bash
# Quick site analysis
python scrapers/psense/web/run_scraper.py https://example.com --profile quick

# Balanced crawling (recommended)
python scrapers/psense/web/run_scraper.py https://example.com --profile balanced

# UAE Tax Authority (Arabic/English)
python scrapers/psense/web/run_scraper.py https://tax.gov.ae/en/taxes --profile tax_gov_ae
python scrapers/psense/web/run_scraper.py https://tax.gov.ae/ar/taxes --profile tax_gov_ae

# Multilingual sites
python scrapers/psense/web/run_scraper.py https://example.com --profile multilingual_comprehensive

# List available profiles
python scrapers/psense/web/run_scraper.py --list-profiles

# Show profile details
python scrapers/psense/web/run_scraper.py --show-profile tax_gov_ae

# Custom options
python scrapers/psense/web/run_scraper.py https://example.com --profile balanced \
  --options max_depth=3 concurrency=20 allowed_languages=["en","ar"]

# Dry run (show configuration without scraping)
python scrapers/psense/web/run_scraper.py https://example.com --profile tax_gov_ae --dry-run
```

### Run Parsers (examples)
```python
from parsers.psense.pdf import PDFParser
from pathlib import Path

pdf_path = Path("parsers/psense/pdf/tests/KB.pdf")
doc = PDFParser().parse(pdf_path)
print(doc.to_dict().keys())
```

## 🌐 Multilingual Support

### Features
- **Language Detection**: Automatic detection of Arabic, Chinese, Hindi, Telugu, Japanese, Korean, English
- **Script Analysis**: Unicode-based script identification (Arabic, CJK, Devanagari, etc.)
- **RTL Support**: Right-to-left text processing for Arabic/Hebrew content
- **URL Pattern Recognition**: Automatic language detection from URL patterns (`/ar/`, `/zh/`, etc.)
- **Mixed Content**: Handle multilingual pages with multiple scripts
- **Content Classification**: Language-aware content processing

### Supported Profiles
- **`tax_gov_ae`**: Optimized for UAE Tax Authority (Arabic/English)
- **`multilingual_comprehensive`**: Full multilingual support for international sites
- **`balanced`**: General purpose with basic language support

### Installation for Multilingual
```bash
# Core multilingual dependencies
pip install langdetect chardet ftfy python-bidi

# Enhanced Unicode support
pip install unicodedata2

# Optional: Advanced NLP models
python -m spacy download ar_core_news_sm  # Arabic
python -m spacy download zh_core_web_sm   # Chinese
python -m spacy download ja_core_news_sm  # Japanese
```

### Examples
```bash
# Arabic content
python scrapers/psense/web/run_scraper.py https://tax.gov.ae/ar/ --profile tax_gov_ae

# Chinese content
python scrapers/psense/web/run_scraper.py https://example.com/zh/ --profile multilingual_comprehensive

# Mixed multilingual
python scrapers/psense/web/run_scraper.py https://example.com \
  --options "allowed_languages=['ar','zh','en']" "rtl_support=true"
```

## 🚀 Enhanced Web Scraper Features

### Advanced Infrastructure
- **Circuit Breaker Pattern**: Resilient network operations with failure threshold
- **Database Integration**: SQLite-based session tracking and analytics
- **Content Classification**: AI-powered content type detection
- **Proxy Rotation**: Thread-safe proxy management for load balancing
- **Domain-aware Rate Limiting**: Per-domain request throttling
- **Progress Monitoring**: Visual progress tracking with tqdm
- **Async Support**: aiohttp-based batch processing

### Configuration Profiles
- **`quick`**: Single page analysis (30-60 seconds)
- **`balanced`**: Medium sites, 50-500 pages (5-30 minutes)
- **`comprehensive`**: Large sites with full features (30 minutes - 2 hours)
- **`enterprise`**: Maximum performance for production (1+ hours)
- **`tax_gov_ae`**: Specialized for UAE Tax Authority
- **`multilingual_comprehensive`**: International multilingual sites

## 🧠 Design Intent
**Unified Model First**: All sources map into the same hierarchy: Document → Chapter → Section → Elements (Paragraph/Table/Image/Video/Hyperlink/etc.). Each class exposes consistent methods (`to_dict`, `to_text`, `extract_metadata`, `get_entities`) for downstream use.

**Format Adapters**: Scrapers and file parsers are adapters that translate source-specific structures into the unified model. This enforces consistency and enables reuse of analytics, storage, and APIs.

**Staged Processing** (PDF): The PDF pipeline is organized in stages (layout, OCR, segmentation, metadata, entity extraction, citation parsing) for clarity, testability, and selective execution.

## ⚙️ Dependencies
Runtime dependencies are consolidated in `requirements.txt` and cover:
- **Core web scraping**: `requests`, `beautifulsoup4`, `lxml`, `pandas`, `backoff`, `simhash`
- **Enhanced scraping**: `aiohttp`, `asyncio`, `concurrent.futures`, `tqdm`, `sqlite3`
- **Multilingual support**: `langdetect`, `chardet`, `ftfy`, `python-bidi`, `unicodedata2`
- **NLP/Analysis (optional)**: `spacy`, `textblob`, `polyglot` (+ models as needed)
- **PDF/Docs**: `pdfplumber`, `PyMuPDF` (`fitz`), `camelot-py[cv]`, `python-docx`, `ebooklib`, `markdown`
- **OCR/Imaging**: `opencv-python`, `pytesseract`, `easyocr`, `Pillow`, `numpy`, `paddleocr`, `paddlepaddle`
- **ML/Text correction**: `transformers`, `torch`, `symspellpy`, `fuzzywuzzy`
- **Config/automation**: `PyYAML`, `playwright` (optional), `tqdm`

Some packages require system installs (e.g., Tesseract OCR binary, Ghostscript for Camelot, Playwright browsers). See comments inside `requirements.txt` for notes.

### Graceful Degradation
The scraper gracefully handles missing optional dependencies:
- Without multilingual libraries: Falls back to basic language support
- Without advanced features: Uses lightweight implementations
- Without ML libraries: Skips sentiment analysis and entity extraction

### Enhanced Document Model Integration 🆕

The web scraper now produces **full doc.psense framework documents** with:

#### Rich Document Structure
```json
{
  "id": 1,
  "title": "Page Title",
  "author": null,
  "language": "English",
  "translator": "Original",
  "url": "https://example.com",
  "chapters": [
    {
      "id": 2,
      "title": "Chapter Title",
      "sections": [
        {
          "id": 3,
          "content": [
            {
              "id": 4,
              "text": "Content...",
              "references": [],
              "cache": {},
              "footnotes": null
            }
          ]
        }
      ]
    }
  ],
  "images": [],
  "tables": [],
  "image_content": [],
  "references": [],
  "cache": {},
  "footnotes": null
}
```

#### Advanced Capabilities
- **Unique IDs**: Every element has a unique identifier
- **Metadata Extraction**: ML/NLP-powered metadata analysis
- **Entity Recognition**: Named entity extraction from content
- **Sentiment Analysis**: Document-level sentiment scoring
- **Cross-references**: Element linking and citation support
- **Caching**: Computed metadata caching for performance

#### ML/NLP Integration
```python
from scrapers.psense.web.scraper import WebScraper

with WebScraper(config) as scraper:
    doc = scraper.crawl()
    
    # Extract metadata with ML analysis
    metadata = doc.extract_metadata(['sentiment', 'readability', 'keywords'])
    
    # Get named entities
    entities = doc.get_entities()
    
    # Analyze document sentiment
    sentiment = doc.aggregate_sentiment()
```

## ✅ Testing
All tests are centralized under the top-level `tests/` directory.

- `tests/parsers/` – parser unit/integration tests
- `tests/scrapers/` – web scraper tests
- `tests/parsers/pdf/` – lightweight PDF smoke tests
- `tests/parsers/pdf_assets/` – large PDF assets (moved from `parsers/psense/pdf/tests/`)

Run tests:
```bash
# Run everything (uses pytest.ini -> testpaths=tests)
pytest

# Run parser tests only
pytest tests/parsers -q -s

# Run scraper tests only
pytest tests/scrapers -q -s

# Or with Makefile shortcuts
make test
make test-parsers
make test-scrapers
```

Notes:
- Heavy dependencies (e.g., `pdfplumber`, `fitz`/PyMuPDF, `transformers`) are guarded with `pytest.importorskip`; related tests will be skipped if missing.
- Large binary test assets live in `tests/parsers/pdf_assets/` and are not collected by pytest.

## ♻️ Extensibility
- Add new parser modules under `parsers/psense/<format>/` that emit `doc.psense.document.Document`
- Extend the model in `doc/psense/document/` with new element types implementing the same interface
- Add new scraper profiles or behaviors via `scrapers/psense/web/config.json`

## 🔒 Robustness & Operational Notes
- Staged PDF pipeline enables partial runs and graceful fallbacks when optional deps are missing
- Extensive error handling helpers exist in `parsers/psense/*/error_handler.py`
- Prefer deterministic outputs from adapters to keep the unified model predictable
- Log via the utilities under `parsers/psense/pdf/logging_utils.py` where available

---
Maintained: September 2025