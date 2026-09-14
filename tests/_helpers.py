"""测试公共设施：把 scripts/ 加入 import 路径。

只依赖标准库。jsonschema 是可选的（缺失时 schema 测试自动跳过）。
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def path(*parts) -> str:
    """仓库内的绝对路径。"""
    return os.path.join(ROOT, *parts)
