#!/usr/bin/env python3
"""Life Finds a Way · 1-bit 抖动像素美术生成器。

本仓库的视觉只有两种颜色：黑与白。所有"灰"都由 Bayer 8×8 有序抖动网点表达，
所有图形都由确定性算法绘制——不存在无法复现的画笔痕迹。

    用法：python tools/make_art.py

产物：
    assets/hero-banner-{dark,light}.png   README 主视觉：中文标题烧进图里
    assets/loop-{dark,light}.png          README 的闭环示意图
    assets/evidence-{dark,light}.png      README 证据板：三列数字与状态
    assets/divider-{dark,light}.png       README 章节分隔带
    assets/site/hero.png                  站点首屏背景（无字，文案由 DOM 承担）
    assets/site/fork.png                  提问的方式：一条路分岔，左暗右亮
    assets/site/boundary.png              自主的边界：许可区、边界线、越线尝试
    assets/site/loop-glow.png             闭环：贴着轨道的环状辉光
    assets/site/step-*.png                三站图标：分叉 / 漏斗落点 / 盆里的芽
    assets/site/nebula.png                结尾场景的抖动星云（随滚动位移）
    assets/site/evidence-wall.png         证据墙：状态记号被低频噪声调制出明暗
    assets/site/ring.png                  演化闭环的虚线环

母题（见 docs/design-language.md）：
    避让  文字带（纵向 20%~82%）由 content_band() 主动压暗，美术不与正文抢密度
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


def hero_scene(W, H, seed=7, invert=False):
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

    return upscale(quantize(f, invert=invert))


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



def loop_diagram(W=296, H=139, invert=False):
    """给 README 用的闭环示意图：虚线环 + 三个节点 + 烧进图里的中文标签。"""
    f = field(W, H)
    cx, cy, rx, ry = W / 2, 61, 86, 28
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
    centered("保留", 24, 4)
    centered("选择", 24, H - 30)
    centered("Variation → Selection", 12, int(cy) - 10)
    centered("→ Retention", 12, int(cy) + 12)
    return upscale(img, 3)



def content_band(f, W, H, keep=0.42, top=0.20, bottom=0.82, soft=0.10):
    """正文永远落在中段。把这一带的场值按比例压暗，美术自动避让文字。
    边界用 smoothstep 过渡，避免出现横向硬边。"""
    for y in range(H):
        t = y / max(1, H - 1)
        if t < top - soft or t > bottom + soft:
            k = 1.0
        elif top <= t <= bottom:
            k = keep
        else:
            edge = (top - t) / soft if t < top else (t - bottom) / soft
            e = min(1.0, max(0.0, edge))
            k = keep + (1.0 - keep) * (e * e * (3 - 2 * e))
        for x in range(W):
            f[y][x] *= k



def fork_scene(W=320, H=180, seed=41, invert=False):
    """提问的方式：一条路在画面中央分岔。左边那条暗淡（预先选好的路径），右边那条被点亮。"""
    f = field(W, H)
    rad = value_noise(W, H, 6, seed)
    for y in range(H):
        for x in range(W):
            f[y][x] += 0.03 + (rad[y][x] - 0.5) * 0.07
            k = max(0.0, (y / H - 0.78) / 0.22)
            f[y][x] += k * k * 0.16
    content_band(f, W, H, keep=0.34)
    ox, oy = 0.50 * W, 0.94 * H
    left = [(ox, oy), (0.34 * W, 0.66 * H), (0.16 * W, 0.42 * H), (0.08 * W, 0.22 * H)]
    right = [(ox, oy), (0.68 * W, 0.62 * H), (0.84 * W, 0.36 * H), (0.90 * W, 0.18 * H)]
    carve(f, left, radius=2, factor=0.48)
    polyline(f, left, 0.40, jitter=1.5, seed=seed + 1)
    carve(f, right, radius=2, factor=0.58)
    polyline(f, right, 1.0, jitter=1.0, seed=seed + 2)
    beam(f, (0.46 * W, -0.10 * H), (1.18 * W, 0.70 * H), 0.085 * W, 0.11)
    tx, ty = int(0.90 * W), int(0.16 * H)
    for y in range(ty - 9, ty + 10):
        for x in range(tx - 11, tx + 11):
            if 0 <= x < W and 0 <= y < H:
                d = math.hypot((x - tx) / 11, (y - ty) / 9)
                f[y][x] *= 1.0 - 0.82 * max(0.0, 1.0 - d)
    sprout(f, tx, ty)
    disc(f, int(ox), int(oy), 2.2, 1.0)
    return upscale(quantize(f, invert=invert))


def boundary_scene(W=320, H=180, seed=51, invert=False):
    """自主的边界：顶部是许可区（密网点），一条横向虚线，线以下几乎全黑。
    密集区只占顶部一条——正文要坐在中段的暗底上。"""
    f = field(W, H)
    rad = value_noise(W, H, 7, seed)
    fine = value_noise(W, H, 19, seed + 1)
    ny = int(0.22 * H)
    for y in range(H):
        for x in range(W):
            if y < ny:
                f[y][x] += 0.05 + rad[y][x] * 0.20 * (1 - y / ny)
            else:
                f[y][x] += 0.022 + (fine[y][x] - 0.5) * 0.05
    beam(f, (-0.05 * W, 0.02 * H), (1.05 * W, 0.20 * H), 0.05 * H, 0.11)
    for x in range(0, W, 7):                      # 边界线
        for k in range(4):
            put(f, x + k, ny, 1.0, absolute=True)
            put(f, x + k, ny + 1, 1.0, absolute=True)
    rnd = random.Random(seed)
    for i in range(12):                           # 越线尝试：到线即止
        x = rnd.randrange(int(0.05 * W), int(0.95 * W))
        y0 = rnd.randrange(int(0.07 * H), ny - 8)
        polyline(f, [(x, y0), (x, ny - 4)], 0.5, thickness=1, seed=seed + i)
        disc(f, x, ny - 5, 1.1, 1.0)
    return upscale(quantize(f, invert=invert))


def loop_glow(W=320, H=180, seed=61, invert=False):
    """闭环背景：一圈柔和的抖动辉光，让轨道不悬在纯黑上。"""
    f = field(W, H)
    n = value_noise(W, H, 4, seed)
    m = value_noise(W, H, 13, seed + 1)
    for y in range(H):
        for x in range(W):
            d = math.hypot((x - 0.5 * W) / (0.40 * W), (y - 0.5 * H) / (0.42 * H))
            ring = max(0.0, 1.0 - abs(d - 1.0) * 3.6)
            f[y][x] += ring * ring * (0.07 + 0.13 * n[y][x]) * (0.5 + 0.7 * m[y][x])
            f[y][x] += 0.012 + (m[y][x] - 0.5) * 0.03
    content_band(f, W, H, keep=0.46, top=0.26, bottom=0.86)
    return upscale(quantize(f, invert=invert))


def step_icon(kind, invert=False, S=30, k=4):
    """闭环三站的像素小图标：分叉（变异）/ 漏斗落点（选择）/ 盆里的芽（保留）。"""
    f = field(S, S)
    mid = S // 2
    if kind == "vary":
        for i, dy in enumerate((-9, 0, 9)):
            polyline(f, [(5, mid), (S - 9, mid + dy)], 0.5, thickness=1, seed=i)
            disc(f, S - 7, mid + dy, 2.0, 1.0)
        disc(f, 4, mid, 2.2, 1.0)
    elif kind == "select":
        polyline(f, [(3, 5), (S - 4, 5)], 0.45, thickness=1, seed=1)
        polyline(f, [(3, 5), (mid - 2, mid + 3)], 0.8, thickness=1, seed=2)
        polyline(f, [(S - 4, 5), (mid + 2, mid + 3)], 0.8, thickness=1, seed=3)
        polyline(f, [(mid, mid + 4), (mid, S - 8)], 0.7, thickness=1, seed=4)
        disc(f, mid, S - 5, 2.4, 1.0)
    else:
        polyline(f, [(7, S - 9), (S - 7, S - 9)], 0.55, thickness=1, seed=5)
        polyline(f, [(10, S - 6), (S - 10, S - 6)], 0.40, thickness=1, seed=6)
        polyline(f, [(mid, S - 10), (mid, mid - 1)], 1.0, thickness=1, seed=7)
        polyline(f, [(mid, mid - 1), (mid + 5, mid - 6)], 1.0, thickness=1, seed=8)
        polyline(f, [(mid, mid + 2), (mid - 5, mid - 5)], 1.0, thickness=1, seed=9)
        disc(f, mid + 6, mid - 7, 1.7, 1.0)
        disc(f, mid - 6, mid - 6, 1.7, 1.0)
    return upscale(quantize(f, invert=invert), k)


def hero_banner(W=296, H=138, invert=False, seed=13):
    """README 主视觉：中文标题烧进图里，右侧是被证据选中的那条路。"""
    f = field(W, H)
    rad = value_noise(W, H, 5, seed)
    fine = value_noise(W, H, 17, seed + 1)
    ox, oy = 0.09 * W, 0.88 * H
    for y in range(H):
        for x in range(W):
            g = max(0.0, 1.0 - math.hypot((x - ox) / (0.38 * W), (y - oy) / (0.52 * H)))
            f[y][x] += g * g * 0.28 * (0.5 + 0.9 * rad[y][x])
            k = max(0.0, (y / H - 0.78) / 0.22)
            f[y][x] += k * k * 0.34 * (0.5 + 0.9 * rad[y][x])
            c = max(0.0, 1.0 - math.hypot((x - 0.84 * W) / (0.28 * W), (y - 0.20 * H) / (0.30 * H)))
            f[y][x] += c * (0.5 * rad[y][x] + 0.12) * 0.24
            f[y][x] += 0.03 + (fine[y][x] - 0.5) * 0.09
    beam(f, (-0.02 * W, 0.84 * H), (1.02 * W, 0.24 * H), 0.055 * H, 0.19)
    beam(f, (-0.02 * W, 0.82 * H), (1.02 * W, 0.26 * H), 0.016 * H, 0.13)

    rnd = random.Random(seed)
    dim = []
    for i in range(7):
        t = i / 6
        ex = (0.62 - 0.10 * t) * W + rnd.uniform(-0.02, 0.02) * W
        ey = (0.72 - 0.44 * t) * H + rnd.uniform(-0.02, 0.02) * H
        mx = ox + (ex - ox) * 0.55
        my = oy + (ey - oy) * 0.46
        dim.append([(ox, oy), (mx, my), (ex, ey)])
    lit = [(ox, oy), (0.40 * W, 0.62 * H), (0.66 * W, 0.30 * H)]
    for pts in dim:
        carve(f, pts, radius=1, factor=0.40)
        polyline(f, pts, 0.44, jitter=1.4, seed=rnd.randrange(99999))
    carve(f, lit, radius=2, factor=0.60)
    polyline(f, lit, 1.0, jitter=0.9, seed=seed + 900)
    tx, ty = int(0.70 * W), int(0.20 * H)
    for y in range(ty - 10, ty + 12):
        for x in range(tx - 12, tx + 12):
            if 0 <= x < W and 0 <= y < H:
                d = math.hypot((x - tx) / 12, (y - ty) / 11)
                f[y][x] *= 1.0 - 0.84 * max(0.0, 1.0 - d)
    sprout(f, tx, ty)
    disc(f, int(ox), int(oy), 2.4, 1.0)
    for _ in range(int(W * H * 0.0010)):
        put(f, rnd.randrange(W), rnd.randrange(int(H * 0.42)), 1.0, absolute=True)

    lx, ly = int(0.06 * W), int(0.09 * H)
    darken_ellipse(f, lx + 0.40 * W, ly + 34, 0.44 * W, 0.30 * H, 0.96, feather=1.3)
    img = quantize(f, invert=invert)
    ink = 0 if invert else 1
    stamp_text(img, "LIFE FINDS A WAY", 12, (lx, ly), tracking=1, ink=ink)
    stamp_text(img, "生命会寻求自己的出路", 24, (lx, ly + 20), ink=ink)
    stamp_text(img, "让证据决定什么值得保留。", 12, (lx, ly + 52), ink=ink)
    return upscale(img, 3)


def evidence_board(W=296, H=103, invert=False, seed=71):
    """README 版证据板：三列数字与状态，全部烧进像素字。列宽按 1200px 显示宽度反推。"""
    f = field(W, H)
    n = value_noise(W, H, 5, seed)
    for y in range(H):
        for x in range(W):
            f[y][x] += 0.05 + n[y][x] * 0.07
    beam(f, (0.0, -0.2 * H), (1.0 * H, 1.3 * H), 0.045 * W, 0.07)
    cols = [6, 102, 198]
    for cx in (102, 198):
        for y in range(10, H - 10, 4):
            put(f, cx - 12, y, 1.0, absolute=True)
    img = quantize(f, invert=invert)
    ink = 0 if invert else 1
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))

    def w_of(text, size):
        font = ImageFont.truetype(font_path(), size)
        return int(sum(probe.textlength(c, font=font) for c in text))

    for cx, big, sub, label in (
        (cols[0], "8/10", "vs 7/10", "\u5c0f\u6837\u672c\u63a8\u7ffb\u76f4\u89c9"),
        (cols[1], "FAIL", "BLOCKED", "\u5931\u8d25\u4e5f\u662f\u8bc1\u636e"),
        (cols[2], "PASS", "\u53ea\u662f\u8dd1\u901a", "\u5de5\u7a0b\u4e0d\u7b49\u4e8e\u4ef7\u503c"),
    ):
        # 大字 + 紧随其下的一行小字，避免横向挤压
        stamp_text(img, big, 24, (cx, 20), ink=ink, shadow=None)
        stamp_text(img, sub, 12, (cx, 50), ink=ink, shadow=None)
        stamp_text(img, label, 12, (cx, 72), ink=ink, shadow=None)
    img = upscale(img, 3)
    d = ImageDraw.Draw(img)
    for cx in cols:
        d.line([(cx * 3, 44 * 3), ((cx + 90) * 3, 44 * 3)], fill=ink, width=3)
    return img


def divider(W=296, invert=False):
    """章节分隔：一条虚线，中间一颗小芽。"""
    H = 16
    f = field(W, H)
    for x in range(0, W, 7):
        if 134 <= x <= 158:
            continue
        for k in range(4):
            put(f, x + k, 8, 0.6, absolute=True)
    for yy in range(3, 12):
        put(f, W // 2, yy, 1.0, absolute=True)
    for xx in range(W // 2 - 5, W // 2 + 6):
        put(f, xx, 6, 1.0, absolute=True)
        put(f, xx, 10, 1.0, absolute=True)
    return upscale(quantize(f, invert=invert), 3)



def main():
    out = os.path.join(ROOT, "assets")
    site = os.path.join(out, "site")
    os.makedirs(site, exist_ok=True)

    jobs = [
        (os.path.join(site, "hero.png"), lambda: hero_scene(320, 180, seed=11)),
        (os.path.join(site, "nebula.png"), lambda: nebula(320, 180)),
        (os.path.join(site, "ring.png"), lambda: ring(150, 75)),
        (os.path.join(site, "fork.png"), lambda: fork_scene()),
        (os.path.join(site, "boundary.png"), lambda: boundary_scene()),
        (os.path.join(site, "loop-glow.png"), lambda: loop_glow()),
        (os.path.join(site, "step-vary.png"), lambda: step_icon("vary")),
        (os.path.join(site, "step-select.png"), lambda: step_icon("select")),
        (os.path.join(site, "step-retain.png"), lambda: step_icon("retain")),
        (os.path.join(out, "hero-banner-dark.png"), lambda: hero_banner(invert=False)),
        (os.path.join(out, "hero-banner-light.png"), lambda: hero_banner(invert=True)),
        (os.path.join(out, "evidence-dark.png"), lambda: evidence_board(invert=False)),
        (os.path.join(out, "evidence-light.png"), lambda: evidence_board(invert=True)),
        (os.path.join(out, "divider-dark.png"), lambda: divider(invert=False)),
        (os.path.join(out, "divider-light.png"), lambda: divider(invert=True)),
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