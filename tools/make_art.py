#!/usr/bin/env python3
"""Life Finds a Way · 1-bit 抖动像素美术生成器。

本仓库的视觉只有两种颜色：黑与白。所有"灰"都由 Bayer 8×8 有序抖动网点表达，
所有图形都由确定性算法绘制——不存在无法复现的画笔痕迹。

    用法：python tools/make_art.py

产物：
    assets/hero-dark.png           README 主视觉（黑底白点，含字）
    assets/hero-light.png          README 主视觉（白底黑点，含字）
    assets/site/hero.png           站点首屏背景（无字，文案由 DOM 承担）
    assets/site/nebula.png         结尾场景的抖动星云（随滚动位移）
    assets/site/evidence-wall.png  证据墙：状态记号被低频噪声调制出明暗
    assets/site/ring.png           演化闭环的虚线环

母题（见 docs/design-language.md）：
    分支  多条道路同时存在，绝大多数保持暗淡
    证据  一道斜向光带扫过画面，只有被照到的那条路变成实心
    保留  被照亮的路径尽头，长出一个小小的芽
"""

from __future__ import annotations

import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_CANDIDATES = [
    os.path.join(ROOT, "assets", "fonts", "fusion-pixel-12px-mono-zh-hans.otf"),
    os.path.join(ROOT, ".build", "fusion.otf"),
]
SCALE = 4  # 逻辑像素 → 输出像素的整数倍率
DESIGN_PX = 12  # 字体以 12px 为设计尺寸，只用整数倍渲染

BAYER8 = (
    (0, 32, 8, 40, 2, 34, 10, 42),
    (48, 16, 56, 24, 50, 18, 58, 26),
    (12, 44, 4, 36, 14, 46, 6, 38),
    (60, 28, 52, 20, 62, 30, 54, 22),
    (3, 35, 11, 43, 1, 33, 9, 41),
    (51, 19, 59, 27, 49, 17, 57, 25),
    (15, 47, 7, 39, 13, 45, 5, 37),
    (63, 31, 55, 23, 61, 29, 53, 21),
)


def font_path() -> str:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到像素字体，请先运行 tools/build_font.py")


# --------------------------------------------------------------------------- 场

def field(w: int, h: int, v: float = 0.0) -> list[list[float]]:
    return [[v] * w for _ in range(h)]


def put(f, x, y, v, absolute=False):
    h, w = len(f), len(f[0])
    if 0 <= x < w and 0 <= y < h:
        f[y][x] = v if absolute else min(1.0, f[y][x] + v)


def disc(f, cx, cy, r, v):
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                put(f, x, y, v)


def polyline(f, pts, v, jitter=0.0, seed=0, thickness=1):
    """沿折线逐像素落点。0.5 左右的 v 经抖动后自然成为网点虚线。"""
    rnd = random.Random(seed)
    drift = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
        for i in range(dist + 1):
            t = i / dist
            if jitter:
                drift = max(-jitter, min(jitter, (drift + rnd.uniform(-0.6, 0.6)) * 0.88))
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t + drift
            for k in range(-(thickness // 2), thickness // 2 + 1):
                put(f, int(round(x)), int(round(y)) + k, v)


def carve(f, pts, radius=2, factor=0.6):
    """沿折线把场压出一条暗槽——路要先清出来，才立得住。乘法压暗，场不会变成负值。"""
    h, w = len(f), len(f[0])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dist = max(1, int(math.hypot(x1 - x0, y1 - y0)))
        for i in range(dist + 1):
            t = i / dist
            cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    d = math.hypot(dx, dy)
                    x, y = int(round(cx)) + dx, int(round(cy)) + dy
                    if d <= radius and 0 <= x < w and 0 <= y < h:
                        f[y][x] *= 1.0 - factor * (1.0 - d / (radius + 0.001))


def beam(f, p0, p1, half_width, v, falloff=2.4):
    """斜向光带：离中心轴越远越暗——证据照射的方向感。"""
    h, w = len(f), len(f[0])
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy or 1.0
    for y in range(h):
        for x in range(w):
            t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / l2))
            d = math.hypot(x - (x0 + dx * t), y - (y0 + dy * t))
            if d < half_width:
                put(f, x, y, v * (1.0 - (d / half_width) ** falloff))


def value_noise(w, h, cells, seed):
    rnd = random.Random(seed)
    gw = cells + 2
    grid = [[rnd.random() for _ in range(gw)] for _ in range(gw)]

    def sm(t):
        return t * t * (3 - 2 * t)

    out = field(w, h)
    for y in range(h):
        fy = y / max(1, h - 1) * cells
        y0, ty = int(fy), sm(fy - int(fy))
        for x in range(w):
            fx = x / max(1, w - 1) * cells
            x0, tx = int(fx), sm(fx - int(fx))
            a, b = grid[y0][x0], grid[y0][x0 + 1]
            c, d = grid[y0 + 1][x0], grid[y0 + 1][x0 + 1]
            out[y][x] = (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty
    return out


def darken_ellipse(f, cx, cy, rx, ry, factor, feather=1.6):
    """在文字下压出一块暗池。用椭圆距离而非矩形，抖动后才不会出现硬边方框。"""
    h, w = len(f), len(f[0])
    for y in range(h):
        for x in range(w):
            k = math.hypot((x - cx) / rx, (y - cy) / ry)
            if k < feather:
                f[y][x] *= 1.0 - factor * max(0.0, 1.0 - k / feather)


def quantize(f, invert=False) -> Image.Image:
    h, w = len(f), len(f[0])
    img = Image.new("1", (w, h), 0)
    px = img.load()
    for y in range(h):
        row, by = f[y], BAYER8[y & 7]
        for x in range(w):
            on = row[x] > (by[x & 7] + 0.5) / 64.0
            px[x, y] = (0 if on else 1) if invert else (1 if on else 0)
    return img


def upscale(img: Image.Image, k: int = SCALE) -> Image.Image:
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


# --------------------------------------------------------------------------- 字

def stamp_text(img: Image.Image, text, size_logical, xy, tracking=0, ink=1, shadow=(2, -3)):
    shadow = tuple(shadow) if shadow else (0, 0)
    """在逻辑尺寸的 1-bit 图上落字：先画硬阴影，再落墨（像素字讲硬阴影，不讲羽化）。"""
    font = ImageFont.truetype(font_path(), size_logical)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    width = int(sum(probe.textlength(c, font=font) for c in text) + tracking * max(0, len(text) - 1))
    mask = Image.new("L", (max(1, width + abs(shadow[0]) + 4), int(size_logical * 1.6) + 6), 0)
    md = ImageDraw.Draw(mask)
    x = 0.0
    for ch in text:
        md.text((x, max(0, -shadow[1])), ch, font=font, fill=255)
        x += probe.textlength(ch, font=font) + tracking
    x0, y0 = xy

    def paste(color):
        img.paste(255 if color else 0, (int(x0), int(y0)), mask)

    if shadow:
        x0, y0 = x0 + shadow[0], y0 + shadow[1]
        paste(1 - ink)
        x0, y0 = xy
    paste(ink)
    return width


# --------------------------------------------------------------------------- 场景

def branches(f, W, H, seed=7, count=9):
    """从左下同一处散开的道路，终点沿右侧铺开；最上面那条被点亮。"""
    rnd = random.Random(seed)
    ox, oy = 0.10 * W, 0.84 * H
    dim, fork = [], []
    for i in range(count):
        t = i / (count - 1)
        ex = (0.88 - 0.16 * t) * W + rnd.uniform(-0.03, 0.03) * W
        ey = (0.74 - 0.56 * t) * H + rnd.uniform(-0.03, 0.03) * H
        mx = ox + (ex - ox) * 0.55 + rnd.uniform(-0.04, 0.04) * W
        my = oy + (ey - oy) * 0.46 + rnd.uniform(-0.05, 0.05) * H
        dim.append([(ox, oy), (mx, my), (ex, ey)])
        if i % 2 == 0:  # 走不通的路也会再分叉
            bx = mx + (ex - mx) * 0.5
            by = my + (ey - my) * 0.5
            fork.append([(mx, my), (bx, by),
                         (bx + rnd.uniform(-0.07, 0.07) * W, by - rnd.uniform(0.05, 0.16) * H)])
    lit = dim[-1]  # 被证据选中的那条：扇形里最上面的一条
    dim = dim[:-1]

    for pts in fork:  # 次级分叉：最暗，槽最浅
        carve(f, pts, radius=1, factor=0.30)
        polyline(f, pts, 0.34, jitter=1.2, seed=rnd.randrange(99999))
    for pts in dim:  # 存在的许多可能性：暗槽里的一条网点虚线
        carve(f, pts, radius=1, factor=0.42)
        polyline(f, pts, 0.56, jitter=1.6, seed=rnd.randrange(99999))
    carve(f, lit, radius=2, factor=0.62)  # 被选中的路：更深的槽，实心的线
    polyline(f, lit, 1.0, jitter=0.9, seed=seed + 900)
    return (ox, oy), lit[-1]


def sprout(f, cx, cy, v=1.0):
    """路径尽头的小芽：被保留的东西开始生长。"""
    disc(f, int(cx), int(cy) + 3, 2.2, v)
    polyline(f, [(cx, cy + 3), (cx, cy - 3)], v, thickness=1, seed=1)
    polyline(f, [(cx, cy - 3), (cx + 5, cy - 7)], v, thickness=1, seed=2)
    polyline(f, [(cx, cy - 4), (cx - 5, cy - 8)], v, thickness=1, seed=3)
    disc(f, int(cx + 6), int(cy - 8), 1.4, v)
    disc(f, int(cx - 6), int(cy - 9), 1.4, v)


def hero_scene(W, H, seed=7, with_text=False, invert=False, lockup="LIFE FINDS A WAY"):
    """首屏：起点在左下，多数道路暗淡，一道光带照出被选中的那条。"""
    rad = value_noise(W, H, 5, seed + 1)
    cloud = value_noise(W, H, 3, seed + 7)
    fine = value_noise(W, H, 17, seed + 2)
    f = field(W, H)
    ox, oy = 0.10 * W, 0.84 * H

    for y in range(H):
        for x in range(W):
            # 起点周围的一圈微光：能量只从那里发出
            g = max(0.0, 1.0 - math.hypot((x - ox) / (0.34 * W), (y - oy) / (0.46 * H)))
            f[y][x] += g * g * 0.26 * (0.5 + 0.9 * rad[y][x])
            # 地平线雾带：只贴底，不侵入中景
            k = max(0.0, (y / H - 0.80) / 0.20)
            f[y][x] += k * k * 0.30 * (0.5 + 0.9 * rad[y][x])
            # 右上角远处的一团云：目标所在的方向
            c = max(0.0, 1.0 - math.hypot((x - 0.88 * W) / (0.30 * W), (y - 0.14 * H) / (0.30 * H)))
            f[y][x] += c * (0.55 * cloud[y][x] + 0.10) * 0.26
            f[y][x] += 0.035 + (fine[y][x] - 0.5) * 0.10

    # 光带沿"被选中的路"斜穿画面：窄，且不该把中景冲白
    beam(f, (-0.02 * W, 0.82 * H), (1.02 * W, 0.20 * H), 0.046 * H, 0.17)
    beam(f, (-0.02 * W, 0.80 * H), (1.02 * W, 0.22 * H), 0.015 * H, 0.12)

    origin, target = branches(f, W, H, seed=seed)
    rnd = random.Random(seed + 5)
    for _ in range(int(W * H * 0.0009)):
        put(f, rnd.randrange(W), rnd.randrange(int(H * 0.5)), 1.0, absolute=True)
    # 芽长在终点：先给它凿一块暗底，它才跳得出来
    sx, sy = target[0] + 0.012 * W, target[1] - 0.02 * H
    for y in range(int(sy - 0.16 * H), int(sy + 0.16 * H)):
        for x in range(int(sx - 0.09 * W), int(sx + 0.09 * W)):
            if 0 <= x < W and 0 <= y < H:
                d = math.hypot((x - sx) / (0.09 * W), (y - sy) / (0.16 * H))
                f[y][x] *= 1.0 - 0.86 * max(0.0, 1.0 - d)
    sprout(f, sx, sy)
    disc(f, int(origin[0]), int(origin[1]), 2.6, 1.0)

    tx, ty = int(0.055 * W), int(0.10 * H)
    if with_text:
        darken_ellipse(f, tx + 0.34 * W, ty + DESIGN_PX * 0.5, 0.42 * W, 0.20 * H, 0.9)

    img = quantize(f, invert=invert)
    if with_text:
        stamp_text(img, lockup, DESIGN_PX, (tx, ty), tracking=1, ink=0 if invert else 1)
    return upscale(img)


def nebula(W, H, seed=21, invert=False):
    base = value_noise(W, H, 4, seed)
    mid = value_noise(W, H, 9, seed + 1)
    fine = value_noise(W, H, 23, seed + 2)
    f = field(W, H)
    for y in range(H):
        for x in range(W):
            f[y][x] = max(0.0, base[y][x] * 0.95 + mid[y][x] * 0.5 + (fine[y][x] - 0.5) * 0.20 - 0.62) * 1.05
    beam(f, (0.62 * W, -0.1 * H), (0.30 * W, 1.1 * H), 0.07 * W, 0.30)
    return upscale(quantize(f, invert=invert))


def evidence_wall(W, H, seed=33, invert=False) -> Image.Image:
    """证据墙：一行行状态记号。可见度由低频噪声调制，于是整面墙会明暗呼吸。"""
    tokens = ["PASS", "FAIL", "BLOCKED", "INCONCLUSIVE", "NOT_PROVEN",
              "变异", "选择", "保留", "证据", "基线", "使命", "边界", "授权", "验收"]
    tone = value_noise(W, H, 6, seed)
    rnd = random.Random(seed + 3)
    img = Image.new("1", (W, H), 0)
    font = ImageFont.truetype(font_path(), DESIGN_PX)
    d = ImageDraw.Draw(img)
    y = 4
    while y < H - DESIGN_PX:
        x = -rnd.randrange(0, 60)
        while x < W:
            tk = tokens[rnd.randrange(len(tokens))]
            if tone[min(H - 1, y)][min(W - 1, max(0, x))] > 0.46:
                d.text((x, y), tk, font=font, fill=0 if invert else 1)
            x += int(d.textlength(tk, font=font)) + rnd.choice([10, 16, 22, 30, 38])
        y += 14
    return upscale(img)


def ring(W, H, invert=False, dashes=30, duty=0.42, radius=0.42, thickness=1):
    """虚线环：演化闭环的轨道。抖动只作用于弧线本身，因此看起来是"点线"。"""
    f = field(W, H)
    spread = 360.0 / dashes
    for i in range(dashes):
        a0 = i * spread + spread * (1 - duty) / 2
        steps = max(3, int(duty * spread))
        for s in range(steps + 1):
            a = math.radians(a0 + duty * spread * s / steps)
            x = W / 2 + math.cos(a) * radius * W
            y = H / 2 + math.sin(a) * radius * W * (H / W)
            for k in range(-(thickness // 2), thickness // 2 + 1):
                put(f, int(round(x)), int(round(y)) + k, 1.0, absolute=True)
    return upscale(quantize(f, invert=invert))



def loop_diagram(W=320, H=150, invert=False):
    """给 README 用的闭环示意图：虚线环 + 三个节点 + 烧进图里的中文标签。"""
    f = field(W, H)
    cx, cy, rx, ry = W / 2, 66, 96, 30
    dashes, duty = 34, 0.42
    spread = 360.0 / dashes
    for i in range(dashes):
        a0 = i * spread + spread * (1 - duty) / 2
        steps = max(3, int(duty * spread))
        for k in range(steps + 1):
            a = math.radians(a0 + duty * spread * k / steps)
            put(f, int(round(cx + math.cos(a) * rx)), int(round(cy + math.sin(a) * ry)), 1.0, absolute=True)

    nodes = {"01": (cx - rx, cy), "02": (cx, cy + ry), "03": (cx, cy - ry)}
    for nx, ny in nodes.values():
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                put(f, int(nx) + dx, int(ny) + dy, 1.0, absolute=True)

    img = quantize(f, invert=invert)
    ink = 0 if invert else 1
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))

    def width_of(text, size):
        font = ImageFont.truetype(font_path(), size)
        return int(sum(probe.textlength(c, font=font) for c in text))

    def centered(text, size, y):
        stamp_text(img, text, size, (int(cx - width_of(text, size) / 2), y), ink=ink, shadow=None)

    stamp_text(img, "变异", 24, (6, int(cy) - 14), ink=ink, shadow=None)
    centered("保留", 24, 6)
    centered("选择", 24, H - 32)
    stamp_text(img, "01", 12, (int(cx - rx) + 12, int(cy) - 16), ink=ink, shadow=None)
    stamp_text(img, "02", 12, (int(cx) + 12, int(cy + ry) - 6), ink=ink, shadow=None)
    stamp_text(img, "03", 12, (int(cx) + 12, int(cy - ry) + 4), ink=ink, shadow=None)
    centered("Variation → Selection", 12, int(cy) - 16)
    centered("→ Retention", 12, int(cy) + 4)
    return upscale(img)


def main():
    out = os.path.join(ROOT, "assets")
    site = os.path.join(out, "site")
    os.makedirs(site, exist_ok=True)

    jobs = [
        (os.path.join(out, "hero-dark.png"), lambda: hero_scene(300, 100, with_text=True, invert=False)),
        (os.path.join(out, "hero-light.png"), lambda: hero_scene(300, 100, with_text=True, invert=True)),
        (os.path.join(site, "hero.png"), lambda: hero_scene(320, 180, seed=11, with_text=False)),
        (os.path.join(site, "nebula.png"), lambda: nebula(320, 180)),
        (os.path.join(site, "ring.png"), lambda: ring(150, 75)),
        (os.path.join(site, "evidence-wall.png"), lambda: evidence_wall(320, 180)),
        (os.path.join(out, "loop-dark.png"), lambda: loop_diagram(invert=False)),
        (os.path.join(out, "loop-light.png"), lambda: loop_diagram(invert=True)),
    ]
    for path, fn in jobs:
        img = fn()
        img.save(path, optimize=True)
        print(f"{os.path.relpath(path, ROOT):44s} {img.width:>4}x{img.height:<4} {os.path.getsize(path) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()