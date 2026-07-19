"""Trace pearto.jpeg into silk line art: pear silhouette, face hood, eyes,
mouth, stem. Writes contours (normalized) to pearto_contours.json and a
preview PNG."""
import json
import numpy as np
from PIL import Image, ImageDraw
from collections import deque

SRC = r"C:\Users\Joonatan Alanampa\Downloads\pearto.jpeg"
OUTDIR = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\tools"

img = Image.open(SRC).convert("RGB")
W, H = img.size
a = np.asarray(img).astype(np.float32) / 255.0
r, g, b = a[..., 0], a[..., 1], a[..., 2]
mx = a.max(-1); mn = a.min(-1)
v = mx
s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
# hue
h = np.zeros_like(mx)
d = np.maximum(mx - mn, 1e-6)
m = (mx == r); h[m] = ((g - b)[m] / d[m]) % 6
m = (mx == g); h[m] = (b - r)[m] / d[m] + 2
m = (mx == b); h[m] = (r - g)[m] / d[m] + 4
h *= 60

# 1. white background: flood fill from borders over near-white
near_white = (v > 0.88) & (s < 0.13)
bg = np.zeros((H, W), bool)
dq = deque()
for x in range(W):
    for y in (0, H - 1):
        if near_white[y, x] and not bg[y, x]:
            bg[y, x] = True; dq.append((y, x))
for y in range(H):
    for x in (0, W - 1):
        if near_white[y, x] and not bg[y, x]:
            bg[y, x] = True; dq.append((y, x))
while dq:
    y, x = dq.popleft()
    for yy, xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
        if 0 <= yy < H and 0 <= xx < W and near_white[yy, xx] and not bg[yy, xx]:
            bg[yy, xx] = True; dq.append((yy, xx))

def components(mask):
    lab = np.zeros(mask.shape, int); nxt = 0; sizes = {}
    for y0 in range(mask.shape[0]):
        for x0 in range(mask.shape[1]):
            if mask[y0, x0] and lab[y0, x0] == 0:
                nxt += 1; lab[y0, x0] = nxt; q = deque([(y0, x0)]); n = 1
                while q:
                    y, x = q.popleft()
                    for yy, xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                        if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] \
                           and mask[yy, xx] and lab[yy, xx] == 0:
                            lab[yy, xx] = nxt; n += 1; q.append((yy, xx))
                sizes[nxt] = n
    return lab, sizes

def largest(mask):
    lab, sizes = components(mask)
    if not sizes:
        return np.zeros_like(mask)
    k = max(sizes, key=sizes.get)
    return lab == k

def fill_holes(mask):
    inv = ~mask
    lab, sizes = components(inv)
    out = mask.copy()
    border_labels = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    for k in sizes:
        if k not in border_labels:
            out |= (lab == k)
    return out

pear = fill_holes(largest(~bg))

# 2. face hood: everything inside the pear that is NOT yellow (skip stem area)
yellow = (h > 35) & (h < 90) & (s > 0.2)
interior = pear & ~yellow
interior[:int(H * 0.30), :] = False   # exclude stem region
face = fill_holes(largest(interior))

# 3. eyes: very dark blobs inside face (stricter than hair)
dark = face & (v < 0.42)
lab, sizes = components(dark)
blobs = sorted(sizes.items(), key=lambda kv: -kv[1])
print("very dark blobs:", [(k, n) for k, n in blobs[:6]])
feats = []
for k, n in blobs[:6]:
    ys, xs = np.nonzero(lab == k)
    feats.append({"n": n, "cx": float(xs.mean()), "cy": float(ys.mean())})
    print(f"  blob {k}: n={n} c=({xs.mean():.0f},{ys.mean():.0f}) "
          f"r~{np.sqrt(n / np.pi):.0f}")

# 4. stem: dark outside face, top third
stem = pear & ~face & (v < 0.55)
stem[int(H*0.35):, :] = False
stem = largest(stem)
print("stem px:", stem.sum())

def trace(mask):
    """Moore boundary tracing with backtracking -> outer contour as (x,y)."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return []
    y0 = ys.min(); x0 = xs[ys == y0].min()
    start = (y0, x0)
    # clockwise neighbours starting from W
    nbrs = [(0,-1),(-1,-1),(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1)]
    def inside(p):
        return 0 <= p[0] < mask.shape[0] and 0 <= p[1] < mask.shape[1] and mask[p]
    contour = [start]
    prev = (y0, x0 - 1)
    cur = start
    for _ in range(40000):
        dy, dx = prev[0] - cur[0], prev[1] - cur[1]
        idx = nbrs.index((dy, dx))
        found = False
        for i in range(1, 9):
            cd = nbrs[(idx + i) % 8]
            cand = (cur[0] + cd[0], cur[1] + cd[1])
            if inside(cand):
                pd = nbrs[(idx + i - 1) % 8]
                prev = (cur[0] + pd[0], cur[1] + pd[1])
                cur = cand
                contour.append(cur)
                found = True
                break
        if not found:
            break
        if cur == start and len(contour) > 2:
            break
    return [(c[1], c[0]) for c in contour]

def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    pts = np.array(pts, float)
    keep = np.zeros(len(pts), bool); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        seg = pts[j] - pts[i]
        L = np.hypot(*seg)
        dvec = pts[i+1:j] - pts[i]
        if L < 1e-6:  # closed loop: chord degenerates to a point
            dist = np.hypot(dvec[:, 0], dvec[:, 1])
        else:
            dist = np.abs(seg[0] * dvec[:, 1] - seg[1] * dvec[:, 0]) / L
        k = np.argmax(dist)
        if dist[k] > eps:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return [tuple(p) for p in pts[keep]]

def round_bottom(pts, frac):
    """Replace the contour's lower portion with a smooth half-ellipse belly."""
    ys = [p[1] for p in pts]
    y0, y1 = min(ys), max(ys)
    ysplit = y0 + frac * (y1 - y0)
    n = len(pts)
    # rotate so index 0 is above the split
    k = next(i for i, p in enumerate(pts) if p[1] < ysplit)
    pts = pts[k:] + pts[:k]
    keep = [p for p in pts if p[1] <= ysplit]
    # boundary points: last kept before the removed run and first after
    below = [i for i, p in enumerate(pts) if p[1] > ysplit]
    if not below:
        return pts
    pa = pts[below[0] - 1]
    pb = pts[(below[-1] + 1) % len(pts)]
    cx = (pa[0] + pb[0]) / 2.0
    a = abs(pb[0] - pa[0]) / 2.0
    b_ax = a * 0.9  # near-semicircular belly
    arc = []
    for t in range(1, 24):
        ang = np.pi * t / 24.0
        sgn = 1 if pa[0] > pb[0] else -1
        arc.append((cx + sgn * a * np.cos(ang), ysplit + b_ax * np.sin(ang)))
    out = []
    for p in pts:
        if p[1] <= ysplit:
            out.append(p)
        if p == pa:
            out += arc
    return out

EPS = 2.2
shapes = {}
shapes["pear"] = round_bottom(rdp(trace(pear), EPS), 0.72)
shapes["face"] = round_bottom(rdp(trace(face), EPS), 0.72)
shapes["stem"] = rdp(trace(stem), EPS)

# parametric face features: two biggest very-dark blobs in the upper face
# region are the eyes; the mouth is the small blob below them
eyes = sorted([f for f in feats if f["n"] > 400], key=lambda f: f["cx"])[:2]
r_eye = float(np.mean([np.sqrt(e["n"] / np.pi) for e in eyes])) * 0.85
circles = []
for e in eyes:
    circles.append({"cx": e["cx"], "cy": e["cy"], "r": r_eye, "fill": False})
    circles.append({"cx": e["cx"], "cy": e["cy"], "r": r_eye * 0.45, "fill": True})

# mouth: locate it (looser darkness below the eyes), draw as a smile arc
eye_y = max(e["cy"] for e in eyes)
dark2 = face & (v < 0.58)
dark2[:int(eye_y + 40), :] = False
lab2, sizes2 = components(dark2)
mouth_blobs = sorted(sizes2.items(), key=lambda kv: -kv[1])
print("mouth candidates:", mouth_blobs[:3])
arcs = []
if mouth_blobs and mouth_blobs[0][1] > 30:
    k = mouth_blobs[0][0]
    ys2, xs2 = np.nonzero(lab2 == k)
    mcx, mcy = float(xs2.mean()), float(ys2.mean())
    hw = 32.0   # smile half-width, px
    dip = 14.0  # smile depth, px
    arcs.append({"p1": (mcx - hw, mcy - dip * 0.35),
                 "pm": (mcx, mcy + dip),
                 "p2": (mcx + hw, mcy - dip * 0.35)})
print("circles:", [(round(c['cx']), round(c['cy']), round(c['r'], 1), c['fill'])
                   for c in circles])
for k, v_ in shapes.items():
    print(k, len(v_), "pts")

# preview
pv = Image.new("RGB", (W, H), "white")
dr = ImageDraw.Draw(pv)
for k, pts in shapes.items():
    if len(pts) > 2:
        dr.line(pts + [pts[0]], fill="black", width=2)
for c in circles:
    box = [c["cx"] - c["r"], c["cy"] - c["r"], c["cx"] + c["r"], c["cy"] + c["r"]]
    if c["fill"]:
        dr.ellipse(box, fill="black")
    else:
        dr.ellipse(box, outline="black", width=2)
for a_ in arcs:
    pts = [a_["p1"], a_["pm"], a_["p2"]]
    # quadratic-ish bezier through the 3 pts for preview
    P = np.array(pts, float)
    ctrl = 2 * P[1] - 0.5 * P[0] - 0.5 * P[2]
    curve = [(float((1-t)**2*P[0][0] + 2*(1-t)*t*ctrl[0] + t**2*P[2][0]),
              float((1-t)**2*P[0][1] + 2*(1-t)*t*ctrl[1] + t**2*P[2][1]))
             for t in np.linspace(0, 1, 20)]
    dr.line(curve, fill="black", width=3)
pv.save(OUTDIR + r"\pearto_preview.png")

json.dump({"polylines": {k: [(round(float(x), 1), round(float(y), 1))
                             for (x, y) in pts]
                         for k, pts in shapes.items()},
           "circles": circles, "arcs": arcs, "size": [W, H]},
          open(OUTDIR + r"\pearto_contours.json", "w"))
print("saved preview + contours;  image", W, "x", H)
