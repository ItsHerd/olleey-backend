#!/usr/bin/env python3
"""
Development server wrapper that suppresses deprecation warnings
"""
import warnings
import sys
import os

# Suppress specific warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.*')
warnings.filterwarnings('ignore', category=Warning, module='urllib3.*')

# Set environment variable to reduce warning verbosity
os.environ['PYTHONWARNINGS'] = 'ignore::FutureWarning,ignore::DeprecationWarning'

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["./routers", "./services", "./schemas", "./middleware", "./utils", "./scripts"],
        reload_includes=["*.py", ".env"],
        log_level="info"
    )
