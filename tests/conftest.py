"""Test configuration and shared fixtures."""

import os
import sys

# Ensure src/ is importable when running tests directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
