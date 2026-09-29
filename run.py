#!/usr/bin/env python3
"""
OSINT Investigation Copilot CLI Launcher
"""
import sys
from app.main import run_app

if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
