#!/usr/bin/env python3
"""提交前统一自检（§16 流程护栏）。

    python3 scripts/preflight.py        # 或： python3 -m scripts.preflight

顺序：清理字节码 → 编译全部 py → 跑全部单元测试 → 校验 skill 包结构。
**任何一步失败就退出非 0**：local verify green → commit → push。
"""
from __future__ import annotations

import compileall
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _clean_pycache() -> None:
    for base, dirs, _files in os.walk(ROOT):
        if ".git" in base:
            continue
        for d in list(dirs):
            if d == "__pycache__":
                p = os.path.join(base, d)
                for f in os.listdir(p):
                    os.remove(os.path.join(p, f))
                os.rmdir(p)
                dirs.remove(d)


def _validate_skill() -> tuple:
    """skill 结构校验（找不到校验脚本就跳过，不算失败）。"""
    cand = ("/Applications/WorkBuddy.app/Contents/Resources/app.asar.unpacked/resources/"
            "plugins/workbuddy-builtin/skills/skill-creator/scripts/quick_validate.py")
    if not os.path.exists(cand):
        return True, "跳过（本机没有 quick_validate.py）"
    for exe in (sys.executable,):
        r = subprocess.run([exe, cand, ROOT], capture_output=True, text=True)
        if r.returncode == 0:
            return True, r.stdout.strip()
    return False, (r.stdout + r.stderr).strip()


def main() -> int:
    print("== preflight ==")
    _clean_pycache()
    print("1/3 compile …", end=" ")
    ok = compileall.compile_dir(os.path.join(ROOT, "scripts"), quiet=1)
    ok = compileall.compile_dir(os.path.join(ROOT, "tests"), quiet=1) and ok
    print("OK" if ok else "FAIL")
    if not ok:
        return 1

    print("2/3 unit tests …")
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(ROOT, "tests"), top_level_dir=os.path.join(ROOT, "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        print("\npreflight FAILED —— 不要提交（local verify green → commit → push）")
        return 1

    print("3/3 skill package …", end=" ")
    ok, msg = _validate_skill()
    print(msg if ok else "FAIL")
    if not ok:
        return 1
    _clean_pycache()
    print("\npreflight PASSED —— 可以 commit / push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
