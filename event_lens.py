"""event-lens 命令行入口（``python -m event_lens``）。

实际的子命令实现在仓库根目录的 ``__main__.py``，这里只是把它暴露成一个
可导入、可 ``-m`` 调用的模块名，让命令行名字和产品名一致。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_cli():
    """把根目录的 __main__.py 作为模块加载（它的文件名不便直接 import）。"""
    path = Path(__file__).resolve().parent / "__main__.py"
    spec = importlib.util.spec_from_file_location("event_lens_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None) -> int:
    return _load_cli().main(argv)


if __name__ == "__main__":
    sys.exit(main())
