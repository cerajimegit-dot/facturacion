#!/usr/bin/env python
"""Clear Streamlit cache to force reload of modules."""
import shutil
import os
from pathlib import Path

def clear_streamlit_cache():
    """Remove .streamlit cache directory."""
    cache_dir = Path.home() / ".streamlit/cache"
    
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"✅ Cleared Streamlit cache: {cache_dir}")
    else:
        print(f"ℹ️  Cache directory not found: {cache_dir}")
    
    # Also try to clear Python __pycache__
    for pycache in Path.cwd().rglob("__pycache__"):
        try:
            shutil.rmtree(pycache)
            print(f"✅ Cleared: {pycache}")
        except:
            pass
    
    print("\n✅ Done! Restart Streamlit to apply changes.")

if __name__ == "__main__":
    clear_streamlit_cache()
