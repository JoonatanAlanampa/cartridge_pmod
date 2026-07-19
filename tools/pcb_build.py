"""Board surgery: delete PSRAM B, extend outline right, add audio parts.
Run with KiCad 10 bundled python. Equivalent of Update-PCB-from-Schematic
plus initial placement; routing is done afterwards."""
import pcbnew

PCB = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb"
STD = r"C:\Users\Joonatan Alanampa\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints"
PRJ = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge"
FMM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))

b = pcbnew.LoadBoard(PCB)

# ---------- 1. delete PSRAM B footprints
for ref in ("U3", "C3", "C4"):
    fp = b.FindFootprintByReference(ref)
    if fp:
        b.RemoveNative(fp)
        print(f"removed {ref}")

# ---------- 2. extend outline: drop right edge (2 arcs + line), stretch top/bottom
to_del = []
for d in b.GetDrawings():
    if d.GetLayerName() != "Edge.Cuts":
        continue
    s, e = d.GetStart(), d.GetEnd()
    xs = sorted([pcbnew.ToMM(s.x), pcbnew.ToMM(e.x)])
    if xs[0] > 169.0:  # right-edge line and both right corner arcs
        to_del.append(d)
for d in to_del:
    b.Remove(d)
print(f"removed {len(to_del)} right-edge shapes")

for d in b.GetDrawings():
    if d.GetLayerName() != "Edge.Cuts":
        continue
    s, e = d.GetStart(), d.GetEnd()
    for pt, setter in ((s, d.SetStart), (e, d.SetEnd)):
        if pcbnew.ToMM(pt.x) > 169.0:
            setter(pcbnew.VECTOR2I(FMM(192.0), pt.y))
            print("stretched line endpoint to x=192")

def add_line(p1, p2):
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(V(*p1)); sh.SetEnd(V(*p2))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(FMM(0.1))
    b.Add(sh)

def add_arc(start, mid, end):
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_ARC)
    sh.SetArcGeometry(V(*start), V(*mid), V(*end))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(FMM(0.1))
    b.Add(sh)

add_arc((192.0, 74.71), (192.7071, 75.0029), (193.0, 75.71))
add_line((193.0, 75.71), (193.0, 93.70))
add_arc((193.0, 93.70), (192.7071, 94.4071), (192.0, 94.70))

# ---------- 3. nets
def net(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
    return n

NETMAP = {
    "L1":  {"1": "+3.3V", "2": "AUDIO_VCCA"},
    "C8":  {"1": "AUDIO_VCCA", "2": "GND"},
    "C9":  {"1": "AUDIO_VCCA", "2": "GND"},
    "U4":  {"1": "AUDIO_VCCA", "2": "PMOD8", "3": "GND", "4": "AUDIO_BUF",
            "5": "AUDIO_VCCA"},
    "R4":  {"1": "AUDIO_N1", "2": "AUDIO_BUF"},
    "C10": {"1": "AUDIO_N1", "2": "GND"},
    "C11": {"1": "AUDIO_N1", "2": "GND"},
    "R5":  {"1": "AUDIO_N2", "2": "AUDIO_N1"},
    "C12": {"1": "AUDIO_N2", "2": "GND"},
    "RV1": {"1": "", "2": "AUDIO_N2", "3": "GND"},
    "C13": {"1": "AUDIO_OUT", "2": "AUDIO_N2"},
    "R6":  {"1": "AUDIO_OUT", "2": "GND"},
    "J3":  {"1": "GND", "2": "AUDIO_OUT", "3": "AUDIO_OUT"},
}

# ---------- 4. footprints: (ref, value, lib, fpname, x, y, rot)
PARTS = [
    ("L1",  "MLF2012-3R3K",    STD + r"\Inductor_SMD.pretty",       "L_0805_2012Metric",   172.0, 76.3, 0),
    ("C8",  "10uF",            STD + r"\Capacitor_SMD.pretty",      "C_0805_2012Metric",   174.4, 76.3, 0),
    ("C9",  "100nF",           STD + r"\Capacitor_SMD.pretty",      "C_0603_1608Metric",   176.6, 76.3, 0),
    ("U4",  "74LVCE1G126SE-7", STD + r"\Package_TO_SOT_SMD.pretty", "SOT-353_SC-70-5",     173.0, 79.4, 0),
    ("R4",  "120R",            STD + r"\Resistor_SMD.pretty",       "R_0603_1608Metric",   176.4, 79.4, 0),
    ("C10", "100nF",           STD + r"\Capacitor_SMD.pretty",      "C_0603_1608Metric",   172.2, 82.0, 90),
    ("C11", "47nF",            STD + r"\Capacitor_SMD.pretty",      "C_0603_1608Metric",   174.6, 82.0, 90),
    ("R5",  "33R",             STD + r"\Resistor_SMD.pretty",       "R_0603_1608Metric",   177.0, 82.0, 90),
    ("C12", "100nF",           STD + r"\Capacitor_SMD.pretty",      "C_0603_1608Metric",   172.2, 84.5, 90),
    ("C13", "47uF",            STD + r"\Capacitor_SMD.pretty",      "C_0805_2012Metric",   175.4, 84.5, 0),
    ("RV1", "3362P-1-201LF",   PRJ + r"\LCSC.pretty",               "TRIM_3362P-1-102",    174.6, 89.6, 0),
    ("R6",  "470R",            STD + r"\Resistor_SMD.pretty",       "R_0603_1608Metric",   183.2, 92.6, 0),
    ("J3",  "PJ-320B",         PRJ + r"\LCSC.pretty",               "BOOMELE_PJ-320B",     184.72, 84.7, 180),
]

for (ref, val, lib, name, x, y, rot) in PARTS:
    fp = pcbnew.FootprintLoad(lib, name)
    assert fp is not None, f"load fail {name}"
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)
    for pad in fp.Pads():
        nm = NETMAP[ref].get(pad.GetNumber(), "")
        if nm:
            pad.SetNet(net(nm))
    b.Add(fp)
    print(f"added {ref} at ({x},{y}) rot {rot}")

pcbnew.SaveBoard(PCB, b)
print("saved")
