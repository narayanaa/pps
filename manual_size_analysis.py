#!/usr/bin/env python3
"""
Manual Project Size Analysis
Based on observed directory contents and file sizes
"""

import os
from pathlib import Path

def manual_size_analysis():
    """Manual analysis based on observed file sizes"""
    
    print("📊 WEB SCRAPER PROJECT - SIZE ANALYSIS")
    print("="*60)
    
    # Based on earlier directory listings, here are the large files observed:
    large_files_observed = [
        ("scraped_output_tax_gov_ae.json", "2885.0KB", "~2.9MB", "Tax scraping output"),
        ("output.txt", "2927.7KB", "~2.9MB", "Text output file"),
        ("scraper.log", "44.7KB", "Log file"),
        ("README.md", "10.4KB", "Documentation"),
        ("config.json", "9.8KB", "Configuration"),
        ("analyze_project_size.py", "7.9KB", "This analysis script"),
        ("test_multilingual_integration.py", "7.4KB", "Test file"),
        ("integration_summary.py", "9.4KB", "Integration summary"),
        ("multilingual_integration_summary.json", "5.5KB", "Integration results"),
        ("output.json", "5.1KB", "JSON output"),
        ("standalone_test_output.json", "4.1KB", "Test output"),
        ("requirements.txt", "3.3KB", "Dependencies"),
        ("run_scraper.py", "2.2KB", "Main runner"),
    ]
    
    print("\n🗂️  LARGEST FILES BY SIZE:")
    print("-" * 50)
    total_size = 0
    for i, (filename, size_str, size_mb, description) in enumerate(large_files_observed, 1):
        # Convert size to bytes for calculation
        if "KB" in size_str:
            size_kb = float(size_str.replace("KB", ""))
            size_bytes = int(size_kb * 1024)
        else:
            size_bytes = 0
        total_size += size_bytes
        
        print(f"   {i:2d}. {size_mb:>8s} - {filename}")
        print(f"       📋 {description}")
    
    print(f"\n📈 DIRECTORY STRUCTURE ANALYSIS:")
    print("-" * 50)
    
    directories = [
        ("scrapers/", "Main scraper modules", "~500KB+"),
        ("parsers/", "Document parsers (PDF, DOCX, EPUB, etc.)", "~300KB+"),
        ("doc/", "Document framework", "~200KB+"),
        ("tests/", "Test files and assets", "~150KB+"),
        (".cache/", "Cache directory (29 items)", "~100KB+"),
        (".pytest_cache/", "Pytest cache", "~50KB+"),
        ("notes/", "Documentation and notes", "~30KB+"),
    ]
    
    for dirname, description, estimated_size in directories:
        print(f"   📁 {dirname:<20s} {estimated_size:>10s} - {description}")
    
    print(f"\n📄 FILE TYPE BREAKDOWN:")
    print("-" * 50)
    
    file_types = [
        (".json", "JSON files", "~3.0MB", "Output files, configs"),
        (".txt", "Text files", "~2.9MB", "Raw output data"),
        (".py", "Python files", "~150KB", "Source code"),
        (".md", "Markdown files", "~15KB", "Documentation"),
        (".log", "Log files", "~45KB", "Runtime logs"),
        ("no_ext", "Other files", "~20KB", "Various"),
    ]
    
    for ext, type_name, total_size, description in file_types:
        print(f"   {ext:>8s}: {total_size:>8s} - {description}")
    
    print(f"\n💡 SIZE OPTIMIZATION RECOMMENDATIONS:")
    print("-" * 50)
    
    recommendations = [
        ("🗑️  Large Output Files", [
            "scraped_output_tax_gov_ae.json (2.9MB) - Archive or compress after analysis",
            "output.txt (2.9MB) - Consider removing if no longer needed",
            "These are the largest files and can be safely removed/archived"
        ]),
        ("🧹 Cache Cleanup", [
            ".cache/ directory - Can be regenerated automatically",
            ".pytest_cache/ - Safe to delete, recreated on next test run",
            "__pycache__/ directories - Can be cleaned with: find . -name '__pycache__' -type d -exec rm -rf {} +"
        ]),
        ("📝 Log Management", [
            "scraper.log (45KB) - Archive old logs periodically",
            "Consider log rotation for production use"
        ]),
        ("📦 Space Optimization", [
            "Compress large JSON output files with gzip",
            "Use .gitignore to exclude output files from version control",
            "Consider implementing automatic cleanup of old output files"
        ])
    ]
    
    for category, items in recommendations:
        print(f"\n   {category}:")
        for item in items:
            print(f"      • {item}")
    
    print(f"\n🎯 CLEANUP COMMANDS:")
    print("-" * 50)
    print("   # Remove cache directories:")
    print("   find . -name '__pycache__' -type d -exec rm -rf {} +")
    print("   rm -rf .cache .pytest_cache")
    print()
    print("   # Archive large output files:")
    print("   gzip scraped_output_tax_gov_ae.json")
    print("   gzip output.txt")
    print()
    print("   # Clean up test outputs:")
    print("   rm -f *test_output*.json standalone_test_output.json")
    
    print(f"\n📊 ESTIMATED TOTAL PROJECT SIZE: ~6-8MB")
    print("   (Largest components: scraped output files ~6MB)")
    
    print(f"\n✅ ANALYSIS COMPLETE")
    print("   Most space is taken by output files from scraping sessions.")
    print("   The core codebase is relatively lightweight (~500KB).")

if __name__ == "__main__":
    manual_size_analysis()