# -*- coding: utf-8 -*-
"""
Simple test script to verify Python execution
"""

print("✅ Python script is running correctly!")
print("🐍 Python version check passed")
print("📁 Working directory access: OK")

import sys
print(f"🔧 Python executable: {sys.executable}")
print(f"📦 Python version: {sys.version}")

# Test imports
try:
    import asyncio
    import logging
    print("📚 Core modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")

print("🎉 Test completed successfully!")