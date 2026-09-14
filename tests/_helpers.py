"""测试公共设施：把 scripts/ 加入 import 路径。

只依赖标准库。jsonschema 是可选的（缺失时 schema 测试自动跳过）。
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
EXAMPLES = os.path.join(ROOT, "examples")
SCHEMAS = os.path.join(ROOT, "schemas")
REFERENCES = os.path.join(ROOT, "references")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def path(*parts) -> str:
    return os.path.join(ROOT, *parts)


def has_jsonschema() -> bool:
    try:
        import jsonschema  # noqa: F401
        return True
    except Exception:                                    # noqa: BLE001
        return False
