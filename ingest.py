#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure src directory is in sys.path when running from repository root
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from anodyne_discord_bot.ingest import main

if __name__ == "__main__":
	main()
