"""Derive the netlist of a KiCad schematic from wires+junctions+labels+pins.
Prints nets so connectivity can be reviewed without KiCad/ERC."""
import re, sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_sch"
text = open(path, encoding="utf-8").read()

# ---------- tokenize into nested s-expr
def parse(s):
    toks = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+', s)
    def helper(i):
        assert toks[i] == "("
        node = []
        i += 1
        while toks[i] != ")":
            if toks[i] == "(":
                child, i = helper(i)
                node.append(child)
            else:
                node.append(toks[i].strip('"'))
                i += 1
        return node, i + 1
    node, _ = helper(0)
    return node

root = parse(text)

def children(node, tag):
    return [c for c in node if isinstance(c, list) and c and c[0] == tag]

def child(node, tag):
    c = children(node, tag)
    return c[0] if c else None

# ---------- lib pin geometry: lib_id -> [(pin_number, px, py)]
libpins = defaultdict(list)
libs = child(root, "lib_symbols")
for sym in children(libs, "symbol"):
    name = sym[1]
    for sub in children(sym, "symbol"):
        for pin in children(sub, "pin"):
            at = child(pin, "at")
            num = child(pin, "number")
            libpins[name].append((num[1], float(at[1]), float(at[2])))
    # pins directly on symbol (rare)
    for pin in children(sym, "pin"):
        at = child(pin, "at")
        num = child(pin, "number")
        libpins[name].append((num[1], float(at[1]), float(at[2])))

def delta(px, py, rot, mx, my):
    if mx:  # mirror x (vertical flip in kicad terms)
        py = -py
    if my:  # mirror y
        px = -px
    rot = rot % 360
    if rot == 0:
        return (px, -py)
    if rot == 90:
        return (-py, -px)
    if rot == 180:
        return (-px, py)
    return (py, px)

# ---------- instances -> absolute pin positions
P = lambda v: round(float(v), 2)
pins = []          # (x, y, "REF.pin")
powernets = []     # (x, y, netname) from power symbols
for sym in children(root, "symbol"):
    lib = child(sym, "lib_id")[1]
    at = child(sym, "at")
    x, y = float(at[1]), float(at[2])
    rot = float(at[3]) if len(at) > 3 else 0
    mir = child(sym, "mirror")
    mx = bool(mir and "x" in mir[1:])
    my = bool(mir and "y" in mir[1:])
    ref = val = "?"
    for prop in children(sym, "property"):
        if prop[1] == "Reference":
            ref = prop[2]
        if prop[1] == "Value":
            val = prop[2]
    for (num, px, py) in libpins.get(lib, []):
        dx, dy = delta(px, py, rot, mx, my)
        ax, ay = round(x + dx, 2), round(y + dy, 2)
        if lib.startswith("power:"):
            powernets.append((ax, ay, val))
        else:
            pins.append((ax, ay, f"{ref}.{num}"))

# ---------- wires / junctions / labels
wires = []
for w in children(root, "wire"):
    pts = child(w, "pts")
    xy = children(pts, "xy")
    wires.append(((P(xy[0][1]), P(xy[0][2])), (P(xy[1][1]), P(xy[1][2]))))
junctions = [(P(j[1][1]), P(j[1][2])) for j in
             [child(j, "at") for j in children(root, "junction")]]
labels = []
for tag in ("label", "global_label"):
    for l in children(root, tag):
        at = child(l, "at")
        labels.append((P(at[1]), P(at[2]), l[1]))
noconn = [(P(child(n, "at")[1]), P(child(n, "at")[2]))
          for n in children(root, "no_connect")]

# ---------- union-find over points
parent = {}
def find(p):
    parent.setdefault(p, p)
    while parent[p] != p:
        parent[p] = parent[parent[p]]
        p = parent[p]
    return p
def union(a, b):
    parent[find(a)] = find(b)

def on_seg(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    if abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) > 0.01:
        return False
    return min(ax, bx) - 0.01 <= px <= max(ax, bx) + 0.01 and \
           min(ay, by) - 0.01 <= py <= max(ay, by) + 0.01

for a, b in wires:
    union(a, b)
# endpoints or junctions or pins landing on wire middles connect
attach_pts = set(junctions) | {(x, y) for (x, y, _) in pins} | \
             {(x, y) for (x, y, _) in labels} | \
             {(x, y) for (x, y, _) in powernets} | \
             {p for w in wires for p in w}
for p in attach_pts:
    for a, b in wires:
        if on_seg(p, a, b):
            union(p, a)

# ---------- build nets
members = defaultdict(list)
for (x, y, name) in pins:
    members[find((x, y))].append(name)
names = defaultdict(set)
for (x, y, n) in labels:
    names[find((x, y))].add(n)
for (x, y, n) in powernets:
    names[find((x, y))].add(n)

allroots = set(members) | set(names)
netlist = []
for r in allroots:
    nm = "/".join(sorted(names.get(r, []))) or "(unnamed)"
    netlist.append((nm, sorted(members.get(r, []))))

# merge nets that share a name (global labels/power connect by name);
# unnamed nets stay separate
byname = defaultdict(list)
unnamed_i = 0
for nm, mems in netlist:
    if nm == "(unnamed)":
        if not mems:
            continue
        unnamed_i += 1
        nm = f"(net#{unnamed_i})"
    byname[nm].extend(mems)

for nm in sorted(byname):
    print(f"{nm:26s} {' '.join(sorted(set(byname[nm])))}")

# dangling pins: pins not on any wire/junction point and alone at their coord
coord_count = defaultdict(list)
for (x, y, name) in pins:
    coord_count[(x, y)].append(name)
print("\n-- pins possibly dangling (no wire endpoint, no companion pin) --")
wirepts = {p for w in wires for p in w} | set(junctions)
for (x, y, name) in pins:
    p = (x, y)
    on_wire = any(on_seg(p, a, b) for a, b in wires)
    if not on_wire and len(coord_count[p]) == 1 and \
       not any(lx == x and ly == y for (lx, ly, _) in labels) and \
       not any(px == x and py == y for (px, py, _) in powernets) and \
       p not in noconn:
        print(f"  {name} at ({x},{y})")
