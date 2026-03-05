#!/usr/bin/env python3
"""Wrapper script for backward compatibility - delegates to src/make_runs.py"""

import sys
import os

# Add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run main
from make_runs import main

if __name__ == "__main__":
    main()
