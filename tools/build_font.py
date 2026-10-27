#!/usr/bin/env python3
"""把页面用到的字形从 Fusion Pixel 12px Mono 里子集出来，产出可离线自带的 woff2。

为什么需要这一步：像素字体必须按设计尺寸（12px 的整数倍）渲染才锐利，
所以站点不引用任何在线字体，而是自带一份只包含页面实际字符的子集——几 KB 而不是 4.8 MB。

    依赖：  pip install fonttools brotli
    用法：  python tools/build_font.py            # 扫描 index.html
            python tools/build_font.py README.md  # 也可以额外扫描其它文件

授权：  上游字体为 SIL OFL 1.1（见 assets/fonts/LICENSE-OFL.txt）。
        子集属于修改版本，因此不沿用原字体名，输出名与页面中的 font-family 均为
        "LFAW Pixel"，仅本仓库内部使用。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CANDIDATES = [
    os.path.join(ROOT, "assets", "fonts", "fusion-pixel-12px-mono-zh-hans.otf"),
    os.path.join(ROOT, ".build", "fusion.otf"),
]
OUT = os.path.join(ROOT, "assets", "fonts", "lfaw-pixel-mono-subset.woff2")

# 页面之外的兜底字符：数字、拉丁、中英文标点——避免任何动态文本掉出字体
EXTRA = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "　、。〈〉《》「」『』【】〔〕！？：；，．·—…–‥“”‘’¥·×÷→←↑↓≠≥≤±°"
    + "0123456789%‰°"
)

STRIP = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
TAGS = re.compile(r"<[^>]+>")


def collect_characters(files: list[str]) -> set[str]:
    chars: set[str] = set(EXTRA)
    for path in files:
        if not os.path.exists(path):
            print(f"跳过（不存在）：{path}")
            continue
        text = open(path, encoding="utf-8").read()
        text = STRIP.sub(" ", text)
        text = TAGS.sub(" ", text)
        chars.update(text)
    chars.discard("\n")
    chars.discard("\t")
    return {c for c in chars if c.strip() or c == " "}


def main() -> None:
    src = next((p for p in SRC_CANDIDATES if os.path.exists(p)), None)
    if not src:
        raise SystemExit("找不到源字体：请把 fusion-pixel-12px-mono-zh-hans.otf 放到 assets/fonts/ 或 .build/")

    targets = [os.path.join(ROOT, "index.html")] + [os.path.join(ROOT, a) for a in sys.argv[1:]]
    chars = collect_characters(targets)
    text = "".join(sorted(chars))
    print(f"源字体：{os.path.relpath(src, ROOT)}")
    print(f"扫描文件：{[os.path.relpath(t, ROOT) for t in targets]}")
    print(f"字形数：{len(chars)}")

    cmd = [
        sys.executable, "-m", "fontTools.subset", src,
        f"--text={text}",
        "--layout-features=*",
        "--no-hinting" if False else "--desubroutinize",
        "--flavor=woff2",
        f"--output-file={OUT}",
    ]
    subprocess.run(cmd, check=True)
    size = os.path.getsize(OUT)
    print(f"输出：{os.path.relpath(OUT, ROOT)}  {size / 1024:.1f} KB（原始 {os.path.getsize(src) / 1024 / 1024:.1f} MB）")


if __name__ == "__main__":
    main()