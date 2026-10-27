"""把逐帧拍摄的 PNG 序列压成 1-bit 调色板的 GIF。

设计只有两三个灰阶，所以这里不用自适应调色板，而是把每一帧量化到同一组固定色，
避免帧间调色板漂移导致的闪烁，也让 GIF 的 LZW 压缩更有效。
"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".build" / "frames" / "journey"
OUT = ROOT / "assets" / "media" / "journey.gif"

PALETTE = [
    (0, 0, 0), (255, 255, 255),
    (122, 122, 122), (79, 79, 79),
    (157, 157, 157), (168, 168, 168),
    (207, 207, 207), (232, 232, 232),
]


def palette_image() -> Image.Image:
    p = Image.new("P", (1, 1))
    flat = []
    for c in PALETTE:
        flat.extend(c)
    flat.extend([0] * (768 - len(flat)))
    p.putpalette(flat)
    return p


def main(width: int = 720, fps: int = 12, every: int = 1) -> None:
    pal = palette_image()
    files = sorted(SRC.glob("f*.png"))[::every]
    frames = []
    for f in files:
        im = Image.open(f).convert("RGB")
        h = round(im.height * width / im.width)
        im = im.resize((width, h), Image.LANCZOS)
        frames.append(im.quantize(palette=pal, dither=Image.NONE))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / fps * every),
        loop=0,
        optimize=True,
        disposal=1,
    )
    size = OUT.stat().st_size / 1024
    print(f"{OUT.relative_to(ROOT)}  {frames[0].width}x{frames[0].height}  {len(frames)} 帧  {fps} fps  {size:.0f} KB")


if __name__ == "__main__":
    main(
        width=int(sys.argv[1]) if len(sys.argv) > 1 else 720,
        fps=int(sys.argv[2]) if len(sys.argv) > 2 else 12,
        every=int(sys.argv[3]) if len(sys.argv) > 3 else 1,
    )