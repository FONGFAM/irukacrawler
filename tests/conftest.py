"""
tests/conftest.py — Cấu hình chung cho pytest.
"""
import sys
import os

# Đảm bảo thư mục gốc project nằm trong PYTHONPATH
# để import src.xxx hoạt động từ mọi test file
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
