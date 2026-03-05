"""Integration test configuration."""

import sys
import os

# Add backend to path for integration tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
