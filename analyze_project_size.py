#!/usr/bin/env python3
"""
Project Size Analysis Tool
Identifies the largest files and directories in the web scraper project
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import json

def format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(size_bytes)}{size_names[i]}"
    else:
        return f"{size_bytes:.1f}{size_names[i]}"

def get_file_size(filepath: Path) -> int:
    """Get file size safely"""
    try:
        return filepath.stat().st_size
    except (OSError, FileNotFoundError):
        return 0

def get_directory_size(dirpath: Path) -> int:
    """Calculate total size of directory recursively"""
    total = 0
    try:
        for item in dirpath.rglob('*'):
            if item.is_file():
                total += get_file_size(item)
    except (OSError, PermissionError):
        pass
    return total

def analyze_project_sizes(project_root: str) -> dict:
    """Analyze project file and directory sizes"""
    root_path = Path(project_root)
    
    # Large files analysis
    large_files = []
    all_files = []
    hidden_files = []
    cache_files = []
    
    print("🔍 Scanning project files (including hidden)...")
    
    try:
        for item in root_path.rglob('*'):
            if item.is_file():
                size = get_file_size(item)
                rel_path = item.relative_to(root_path)
                all_files.append((str(rel_path), size))
                
                # Track hidden files
                if any(part.startswith('.') for part in item.parts):
                    hidden_files.append((str(rel_path), size))
                
                # Track cache files
                if '__pycache__' in str(rel_path) or '.cache' in str(rel_path) or '.pytest_cache' in str(rel_path):
                    cache_files.append((str(rel_path), size))
                
                # Consider files > 1MB as "large"
                if size > 1024 * 1024:
                    large_files.append((str(rel_path), size))
                # Also track files > 100KB for investigation
                elif size > 100 * 1024:
                    large_files.append((str(rel_path), size))
    except Exception as e:
        print(f"Error scanning files: {e}")
    
    # Sort by size
    all_files.sort(key=lambda x: x[1], reverse=True)
    large_files.sort(key=lambda x: x[1], reverse=True)
    
    # Directory analysis
    directories = []
    print("📁 Analyzing directory sizes...")
    
    try:
        for item in root_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                size = get_directory_size(item)
                directories.append((item.name, size))
    except Exception as e:
        print(f"Error analyzing directories: {e}")
    
    directories.sort(key=lambda x: x[1], reverse=True)
    
    # File type analysis
    file_types = {}
    print("📄 Analyzing file types...")
    
    for filepath, size in all_files:
        ext = Path(filepath).suffix.lower()
        if not ext:
            ext = "no_extension"
        
        if ext not in file_types:
            file_types[ext] = {"count": 0, "total_size": 0, "files": []}
        
        file_types[ext]["count"] += 1
        file_types[ext]["total_size"] += size
        
        # Keep track of largest files of this type
        if len(file_types[ext]["files"]) < 5:
            file_types[ext]["files"].append((filepath, size))
        else:
            # Replace smallest if this one is larger
            min_file = min(file_types[ext]["files"], key=lambda x: x[1])
            if size > min_file[1]:
                file_types[ext]["files"].remove(min_file)
                file_types[ext]["files"].append((filepath, size))
    
    # Sort file types by total size
    file_types_sorted = sorted(file_types.items(), key=lambda x: x[1]["total_size"], reverse=True)
    
    return {
        "all_files": all_files[:50],  # Top 50 largest files
        "large_files": large_files,
        "hidden_files": hidden_files,
        "cache_files": cache_files,
        "directories": directories,
        "file_types": file_types_sorted,
        "total_files": len(all_files),
        "total_project_size": sum(size for _, size in all_files),
        "hidden_size": sum(size for _, size in hidden_files),
        "cache_size": sum(size for _, size in cache_files)
    }

def print_analysis_report(analysis: dict):
    """Print detailed analysis report"""
    
    print("\n" + "="*80)
    print("📊 PROJECT SIZE ANALYSIS REPORT")
    print("="*80)
    
    # Project overview
    total_size = analysis["total_project_size"]
    total_files = analysis["total_files"]
    hidden_size = analysis.get("hidden_size", 0)
    cache_size = analysis.get("cache_size", 0)
    
    print(f"\n📈 PROJECT OVERVIEW:")
    print(f"   Total Files: {total_files:,}")
    print(f"   Total Size: {format_size(total_size)}")
    print(f"   Hidden Files Size: {format_size(hidden_size)}")
    print(f"   Cache Files Size: {format_size(cache_size)}")
    print(f"   Compression Ratio: ~{total_size/1024/1024*0.1:.1f}MB when zipped (estimated)")
    
    # Top 10 largest files
    print(f"\n🗂️  TOP 10 LARGEST FILES:")
    print("-" * 60)
    for i, (filepath, size) in enumerate(analysis["all_files"][:10], 1):
        print(f"   {i:2d}. {format_size(size):>8s} - {filepath}")
    
    # Large files (>1MB)
    if analysis["large_files"]:
        print(f"\n📁 LARGE FILES (>1MB): {len(analysis['large_files'])} files")
        print("-" * 60)
        for filepath, size in analysis["large_files"][:10]:
            print(f"   {format_size(size):>8s} - {filepath}")
    
    # Directory sizes
    print(f"\n📂 DIRECTORY SIZES:")
    print("-" * 60)
    for dirname, size in analysis["directories"][:10]:
        print(f"   {format_size(size):>8s} - {dirname}/")
    
    # File type breakdown
    print(f"\n📄 FILE TYPE BREAKDOWN:")
    print("-" * 60)
    for ext, data in analysis["file_types"][:10]:
        avg_size = data["total_size"] / data["count"] if data["count"] > 0 else 0
        print(f"   {ext:>12s}: {data['count']:>4d} files, {format_size(data['total_size']):>8s} total, {format_size(avg_size):>8s} avg")
    
    # Recommendations
    print(f"\n💡 SIZE OPTIMIZATION RECOMMENDATIONS:")
    print("-" * 60)
    
    # Check for large output files
    large_outputs = [f for f, s in analysis["large_files"] if any(keyword in f.lower() for keyword in ["output", "scraped", "test", "log"])]
    if large_outputs:
        print("   🗑️  Consider cleaning up large output/test files:")
        for filepath in large_outputs[:5]:
            size = next(s for f, s in analysis["large_files"] if f == filepath)
            print(f"      - {filepath} ({format_size(size)})")
    
    # Check for cache directories
    cache_dirs = [d for d, s in analysis["directories"] if "cache" in d.lower() or "__pycache__" in d.lower()]
    if cache_dirs:
        print("   🧹 Cache directories found (can be safely deleted):")
        for dirname in cache_dirs:
            size = next(s for d, s in analysis["directories"] if d == dirname)
            print(f"      - {dirname}/ ({format_size(size)})")
    
    # Check for duplicate files
    json_files = [(f, s) for f, s in analysis["all_files"] if f.endswith('.json')]
    if len(json_files) > 5:
        print(f"   📋 Found {len(json_files)} JSON files - check for duplicates")
    
    log_files = [(f, s) for f, s in analysis["all_files"] if f.endswith('.log')]
    if log_files:
        print(f"   📝 Found {len(log_files)} log files - consider archiving old logs")

def main():
    """Main analysis function"""
    # Get project root (parent of python directory)
    current_dir = Path(__file__).parent
    project_root = current_dir.parent if current_dir.name == "python" else current_dir
    
    print(f"🔍 Analyzing project: {project_root}")
    
    try:
        analysis = analyze_project_sizes(str(project_root))
        print_analysis_report(analysis)
        
        # Save detailed report to file
        report_file = current_dir / "size_analysis_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            # Convert to serializable format
            serializable_analysis = {
                "all_files": analysis["all_files"],
                "large_files": analysis["large_files"], 
                "directories": analysis["directories"],
                "file_types": [(ext, data) for ext, data in analysis["file_types"]],
                "total_files": analysis["total_files"],
                "total_project_size": analysis["total_project_size"]
            }
            json.dump(serializable_analysis, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()