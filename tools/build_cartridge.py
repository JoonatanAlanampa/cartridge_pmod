"""Build cartridge-pmod.kicad_sch from qspi-pmod base + tt-audio-pmod audio chain.

Surgery:
 1. Delete PSRAM B block (U3, decoupling, power, wires, labels, text).
 2. Shrink the PSRAM region rectangle to cover only PSRAM A.
 3. Port the audio chain from tt-audio-pmod, re-placed on a clean grid in the
    freed sheet area, renamed U4/C8-C13/R4-R6/RV1/J3, driven by global label
    PMOD8 (post-CONFIG-jumper side, uio[7]).
 4. Merge required lib_symbols defs from the audio pmod.
 5. Update pinout legend text.
"""
import re, uuid, sys

BASE = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge"
CART = BASE + r"\cartridge-pmod.kicad_sch"
AUDIO = BASE + r"\refs\tt-audio-pmod\tt-audio-pmod.kicad_sch"
PROJ_UUID = "702ec277-2284-48d6-94f3-5b91c08910c1"
PROJ_NAME = "cartridge-pmod"

def new_uuid():
    return str(uuid.uuid4())

cart = open(CART, encoding="utf-8").read().splitlines()
audio = open(AUDIO, encoding="utf-8").read().splitlines()

# ---------- 1. deletion set (1-indexed inclusive ranges, original numbering)
DEL = [
    (1893, 1903),  # text PSRAM B
    (1980, 1985), (2004, 2009), (2010, 2015),  # junctions
    (2028, 2037), (2268, 2277), (2288, 2297), (2318, 2327), (2418, 2427),
    (2478, 2487), (2568, 2577), (2598, 2607), (2608, 2617), (2638, 2647),
    (2688, 2697),  # wires
    (2752, 2773), (2796, 2817), (2862, 2883), (3236, 3257), (3280, 3301),
    (3456, 3477),  # U3 pin labels
    (3500, 3593),  # U3
    (3594, 3665),  # PWR010 +3.3V
    (4099, 4176),  # PWR011 GND
    (4492, 4569),  # C4
    (5507, 5585),  # C3
    (6110, 6187),  # PWR012 GND
]

def grab(lines, a, b):
    return lines[a - 1:b]

# ---------- templates from cartridge file (grab BEFORE delete)
tpl_gnd = grab(cart, 4570, 4635)       # #PWR016 power:GND @ (130.81,161.29)
tpl_33v = grab(cart, 5586, 5651)       # #PWR017 power:+3.3V @ (154.94,180.34)
tpl_lbl = grab(cart, 2994, 3015)       # global_label PMOD8 @ (119.38,190.5)
tpl_rect = grab(cart, 1800, 1811)      # rectangle template
tpl_text = grab(cart, 1871, 1881)      # text 'PMOD' template
tpl_wire = grab(cart, 2028, 2037)      # wire template
tpl_junc = grab(cart, 1962, 1967)      # junction template

# ---------- audio source instance blocks: (lines, src_pos, new_ref, new_pos, new_rot)
# new_rot None = keep source rotation
PORT = [
    ((4547, 4632), (66.04, 104.14), "U4",  (195.58, 167.64), None),  # 74LVC1G126
    ((3361, 3437), (76.20, 82.55),  "L1",  (185.42, 149.86), None),  # ferrite
    ((4388, 4466), (31.75, 86.36),  "C8",  (200.66, 153.67), None),  # 10uF
    ((4050, 4128), (45.72, 86.36),  "C9",  (207.01, 153.67), None),  # 100nF
    ((3582, 3657), (95.25, 104.14), "R4",  (213.36, 167.64), None),  # 120R
    ((4968, 5045), (104.14, 110.49),"C10", (220.98, 171.45), None),  # 100nF
    ((3438, 3515), (116.84, 110.49),"C11", (226.06, 171.45), None),  # 47nF
    ((4699, 4774), (128.27, 104.14),"R5",  (233.68, 167.64), None),  # 33R
    ((5046, 5123), (139.70, 110.49),"C12", (241.30, 171.45), None),  # 100nF
    ((4467, 4546), (180.34, 107.95),"RV1", (246.38, 171.45), None),  # trim 200R
    ((4312, 4387), (205.74, 95.25), "C13", (252.73, 167.64), None),  # 47uF
    ((4129, 4204), (205.74, 107.95),"R6",  (260.35, 171.45), 0),     # 470R -> vertical
    ((4775, 4967), (240.03, 101.60),"J3",  (271.78, 167.64), None),  # PJ-320B jack
]

AT_RE = re.compile(r"\(at (-?[\d.]+) (-?[\d.]+)( [\d.-]+)?\)")

def fnum(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"

def retarget(block, src, ref, dst, rot):
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    out = []
    first_at = True
    for ln in block:
        m = AT_RE.search(ln)
        if m:
            x, y = float(m.group(1)) + dx, float(m.group(2)) + dy
            r = m.group(3) or ""
            if first_at and rot is not None:
                r = f" {rot}"
            ln = ln[:m.start()] + f"(at {fnum(x)} {fnum(y)}{r})" + ln[m.end():]
        if AT_RE.search(block[0] if False else ln) and first_at and "(at" in ln and ln.strip().startswith("(at"):
            first_at = False
        if '"Reference"' in ln:
            ln = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', ln)
        if "(uuid " in ln:
            ln = re.sub(r'\(uuid "[^"]*"\)', f'(uuid "{new_uuid()}")', ln)
        if "(reference " in ln:
            ln = re.sub(r'\(reference "[^"]*"\)', f'(reference "{ref}")', ln)
        if "(project " in ln:
            ln = re.sub(r'\(project "[^"]*"', f'(project "{PROJ_NAME}"', ln)
        if "(path " in ln:
            ln = re.sub(r'\(path "[^"]*"', f'(path "/{PROJ_UUID}"', ln)
        out.append(ln)
    return out

def make_power(tpl, ref, pos):
    src_at = AT_RE.search("\n".join(tpl))
    src = (float(src_at.group(1)), float(src_at.group(2)))
    return retarget(tpl, src, ref, pos, None)

def make_label(tpl, name, pos):
    b = retarget(tpl, (119.38, 190.5), name, pos, None)
    return [re.sub(r'\(global_label "[^"]*"', f'(global_label "{name}"', ln) for ln in b]

def make_wire(p1, p2):
    return ["\t(wire",
            "\t\t(pts",
            f"\t\t\t(xy {fnum(p1[0])} {fnum(p1[1])}) (xy {fnum(p2[0])} {fnum(p2[1])})",
            "\t\t)",
            "\t\t(stroke",
            "\t\t\t(width 0)",
            "\t\t\t(type default)",
            "\t\t)",
            f"\t\t(uuid \"{new_uuid()}\")",
            "\t)"]

def make_junction(p):
    return ["\t(junction",
            f"\t\t(at {fnum(p[0])} {fnum(p[1])})",
            "\t\t(diameter 0)",
            "\t\t(color 0 0 0 0)",
            f"\t\t(uuid \"{new_uuid()}\")",
            "\t)"]

def make_noconnect(p):
    return ["\t(no_connect",
            f"\t\t(at {fnum(p[0])} {fnum(p[1])})",
            f"\t\t(uuid \"{new_uuid()}\")",
            "\t)"]

def make_rect(p1, p2):
    out = []
    for ln in tpl_rect:
        ln = re.sub(r"\(start [-\d. ]+\)", f"(start {fnum(p1[0])} {fnum(p1[1])})", ln)
        ln = re.sub(r"\(end [-\d. ]+\)", f"(end {fnum(p2[0])} {fnum(p2[1])})", ln)
        ln = re.sub(r'\(uuid "[^"]*"\)', f'(uuid "{new_uuid()}")', ln)
        out.append(ln)
    return out

def make_text(s, pos):
    out = []
    for ln in tpl_text:
        ln = ln.replace('"PMOD"', f'"{s}"')
        ln = re.sub(r"\(at [-\d. ]+\)", f"(at {fnum(pos[0])} {fnum(pos[1])} 0)", ln)
        ln = re.sub(r'\(uuid "[^"]*"\)', f'(uuid "{new_uuid()}")', ln)
        out.append(ln)
    return out

# ---------- audio lib_symbols defs to merge
def extract_libdefs(lines, names):
    # lib_symbols block: depth-2 (symbol "name" ...) blocks
    text = "\n".join(lines)
    start = text.index("(lib_symbols")
    defs = {}
    i, depth, cur, curname = start, 0, None, None
    for m in re.finditer(r"[()]", text[start:]):
        pos = start + m.start()
        depth += 1 if m.group() == "(" else -1
        if m.group() == "(" and depth == 2:
            nm = re.match(r'\(symbol "([^"]+)"', text[pos:])
            if nm and nm.group(1) in names:
                cur, curname = pos, nm.group(1)
        elif m.group() == ")" and depth == 1 and cur is not None:
            defs[curname] = text[cur:pos + 1]
            cur = None
        if depth == 0 and pos > start:
            break
    return defs

LIBNAMES = {"74xGxx:74LVC1G126", "PJ-320B:PJ-320B",
            "Device:R_Potentiometer_Trim", "Device:L"}
libdefs = extract_libdefs(audio, LIBNAMES)
missing = LIBNAMES - set(libdefs)
if missing:
    sys.exit(f"missing lib defs: {missing}")

# ---------- assemble new elements
new_elems = []
for (rng, src, ref, dst, rot) in PORT:
    new_elems += retarget(grab(audio, *rng), src, ref, dst, rot)

GNDS = [(200.66, 157.48), (207.01, 157.48), (190.5, 177.8), (220.98, 175.26),
        (226.06, 175.26), (241.3, 175.26), (250.19, 175.26), (260.35, 175.26),
        (264.16, 173.99)]
for i, p in enumerate(GNDS):
    new_elems += make_power(tpl_gnd, f"#PWR0{18 + i}", p)
new_elems += make_power(tpl_33v, "#PWR027", (181.61, 147.32))
new_elems += make_label(tpl_lbl, "PMOD8", (180.34, 167.64))

WIRES = [
    ((181.61, 147.32), (181.61, 149.86)),
    ((189.23, 149.86), (190.5, 149.86)),
    ((190.5, 149.86), (195.58, 149.86)),
    ((195.58, 149.86), (200.66, 149.86)),
    ((200.66, 149.86), (207.01, 149.86)),
    ((190.5, 149.86), (190.5, 157.48)),
    ((195.58, 149.86), (195.58, 157.48)),
    ((208.28, 167.64), (209.55, 167.64)),
    ((217.17, 167.64), (220.98, 167.64)),
    ((220.98, 167.64), (226.06, 167.64)),
    ((226.06, 167.64), (229.87, 167.64)),
    ((237.49, 167.64), (241.3, 167.64)),
    ((241.3, 167.64), (246.38, 167.64)),
    ((246.38, 167.64), (248.92, 167.64)),
    ((256.54, 167.64), (260.35, 167.64)),
    ((260.35, 167.64), (262.89, 167.64)),
    ((262.89, 165.1), (262.89, 167.64)),
    ((262.89, 165.1), (264.16, 165.1)),
    ((262.89, 167.64), (264.16, 167.64)),
    ((250.19, 171.45), (250.19, 175.26)),
    ((264.16, 170.18), (264.16, 173.99)),
]
for w in WIRES:
    new_elems += make_wire(*w)

JUNCS = [(190.5, 149.86), (195.58, 149.86), (200.66, 149.86),
         (220.98, 167.64), (226.06, 167.64), (241.3, 167.64),
         (246.38, 167.64), (260.35, 167.64), (262.89, 167.64)]
for j in JUNCS:
    new_elems += make_junction(j)

new_elems += make_noconnect((246.38, 175.26))  # RV1 pin 3 (rheostat: wiper used)
new_elems += make_rect((176.53, 144.78), (285.75, 180.34))
new_elems += make_text("Audio - PMOD8 / uio[7]", (179.07, 143.51))

# ---------- rebuild file
deleted = set()
for a, b in DEL:
    deleted.update(range(a, b + 1))

out = []
for i, ln in enumerate(cart, 1):
    if i in deleted:
        continue
    if i == 1812 + 0 and "(start" not in ln:
        pass
    # shrink PSRAM rectangle (block 1812-1823): its (end 237.49 142.24)
    if 1812 <= i <= 1823:
        ln = ln.replace("(end 237.49 142.24)", "(end 237.49 91.44)")
    # pinout legend
    if 1938 <= i <= 1948:
        ln = ln.replace("PMOD8 - uio[7] - CS2", "PMOD8 - uio[7] - AUDIO")
    # PSRAM A -> PSRAM (only one left)
    if 1927 <= i <= 1937:
        ln = ln.replace('"PSRAM A"', '"PSRAM"')
    if i == 1799:  # closing of lib_symbols: inject defs before it
        for name in sorted(libdefs):
            for dl in libdefs[name].splitlines():
                out.append("\t\t" + dl if not dl.startswith("\t") else dl)
        out.append(ln)
        continue
    if i == 6188:  # before sheet_instances: inject new elements
        out += new_elems
        out.append(ln)
        continue
    out.append(ln)

open(CART, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print(f"wrote {CART}: {len(out)} lines "
      f"(deleted {len(deleted)}, added {len(new_elems)} element lines, "
      f"{len(libdefs)} lib defs)")
