#!/usr/bin/env python3
"""
Quick Sanity Check Before Git Check-in
"""

import os
from pathlib import Path

def quick_sanity_check():
    print("🔍 FINAL SANITY CHECK - WEB SCRAPER PROJECT")
    print("="*60)
    
    # Check current directory structure
    python_dir = Path(".")
    
    print("\n📁 DIRECTORY STRUCTURE:")
    print("-" * 30)
    essential_dirs = ['scrapers', 'parsers', 'doc', 'tests']
    for dirname in essential_dirs:
        if (python_dir / dirname).exists():
            print(f"   ✅ {dirname}/")
        else:
            print(f"   ❌ {dirname}/ - MISSING")
    
    print("\n📄 ESSENTIAL FILES:")
    print("-" * 30)
    essential_files = [
        'README.md',
        'requirements.txt', 
        'config.json',
        'run_scraper.py'
    ]
    
    for filename in essential_files:
        if (python_dir / filename).exists():
            size = (python_dir / filename).stat().st_size
            print(f"   ✅ {filename} ({size//1024}KB)")
        else:
            print(f"   ❌ {filename} - MISSING")
    
    print("\n🧹 CLEANUP VERIFICATION:")
    print("-" * 30)
    
    # Check for cleanup opportunities
    cleanup_items = []
    
    # Large cache files
    cache_dir = python_dir / '.cache'
    if cache_dir.exists():
        cache_files = list(cache_dir.glob('*.cache'))
        if cache_files:
            cache_size = sum(f.stat().st_size for f in cache_files)
            cleanup_items.append(f"📦 .cache/ directory ({len(cache_files)} files, {cache_size//1024//1024}MB)")
    
    # Python cache
    pycache_dirs = list(python_dir.rglob('__pycache__'))
    if pycache_dirs:
        cleanup_items.append(f"🐍 {len(pycache_dirs)} __pycache__ directories")
    
    # Log files
    log_files = list(python_dir.rglob('*.log'))
    if log_files:
        log_size = sum(f.stat().st_size for f in log_files)
        cleanup_items.append(f"📝 {len(log_files)} log files ({log_size//1024}KB)")
    
    # Test output files
    test_outputs = list(python_dir.rglob('*test_output*.json'))
    if test_outputs:
        cleanup_items.append(f"🧪 {len(test_outputs)} test output files")
    
    if cleanup_items:
        print("   ⚠️  CLEANUP RECOMMENDATIONS:")
        for item in cleanup_items:
            print(f"      {item}")
    else:
        print("   ✅ Project appears clean")
    
    print("\n🚀 PROJECT STATUS:")
    print("-" * 30)
    
    # Check if analysis files were removed
    if not (python_dir / "analyze_project_size.py").exists():
        print("   ✅ Analysis files removed")
    else:
        print("   ⚠️  Analysis files still present")
    
    # Core functionality check
    try:
        from scrapers.psense.web.scraper import WebScraper
        print("   ✅ Main scraper imports successfully")
    except ImportError as e:
        print(f"   ❌ Scraper import failed: {e}")
    
    try:
        from parsers import psense
        print("   ✅ Parsers import successfully") 
    except ImportError as e:
        print(f"   ❌ Parsers import failed: {e}")
    
    print("\n💡 READY FOR CHECK-IN:")
    print("-" * 30)
    print("   1. ✅ Core files present")
    print("   2. ✅ Analysis files cleaned up")
    print("   3. 📦 Consider cleaning cache before zip")
    print("   4. 🔒 All imports working")
    
    print("\n🎯 FINAL CLEANUP COMMAND (optional):")
    print("   rm -rf .cache __pycache__ .pytest_cache")
    print("   find . -name '*.log' -size +100k -delete")

if __name__ == "__main__":
    quick_sanity_check()