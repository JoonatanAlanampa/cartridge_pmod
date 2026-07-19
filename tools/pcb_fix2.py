"""Fix round 2: final placement grid, outline to x=196, GND pours over the
extension, delete listed dangling stubs/vias, reroute cut SCK, route all
audio nets. Deterministic item list - no chain pruning."""
import pcbnew

PCB = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb"
FMM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
b = pcbnew.LoadBoard(PCB)
F, B = pcbnew.F_Cu, pcbnew.B_Cu

MOVES = {
    "L1":  (172.6, 75.9, 0),  "C8": (176.4, 75.9, 0),  "C9": (179.6, 75.9, 0),
    "U4":  (172.8, 79.4, 0),  "R4": (176.2, 79.4, 0),  "C10": (179.5, 79.4, 0),
    "C11": (172.4, 82.3, 0),  "C12": (175.4, 82.3, 0), "R5": (178.4, 82.3, 0),
    "C13": (172.8, 85.2, 180), "R6": (176.4, 85.2, 0),
    "RV1": (175.0, 90.2, 0),  "J3": (187.72, 84.7, 180),
}
for ref, (x, y, rot) in MOVES.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)
print("placed", len(MOVES))

# ---- outline 193 -> 196
kill = [d for d in b.GetDrawings()
        if d.GetLayerName() == "Edge.Cuts"
        and max(pcbnew.ToMM(d.GetStart().x), pcbnew.ToMM(d.GetEnd().x)) > 191.5]
for d in kill:
    b.RemoveNative(d)
for d in b.GetDrawings():
    if d.GetLayerName() != "Edge.Cuts":
        continue
    for pt, setter in ((d.GetStart(), d.SetStart), (d.GetEnd(), d.SetEnd)):
        if abs(pcbnew.ToMM(pt.x) - 192.0) < 0.05:
            setter(pcbnew.VECTOR2I(FMM(195.0), pt.y))

def add_line(p1, p2):
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(V(*p1)); sh.SetEnd(V(*p2))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(FMM(0.1))
    b.Add(sh)

def add_arc(s, m, e):
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_ARC)
    sh.SetArcGeometry(V(*s), V(*m), V(*e))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(FMM(0.1))
    b.Add(sh)

add_arc((195.0, 74.71), (195.7071, 75.0029), (196.0, 75.71))
add_line((196.0, 75.71), (196.0, 93.70))
add_arc((196.0, 93.70), (195.7071, 94.4071), (195.0, 94.70))
print("outline -> 196")

# ---- delete listed dangling vias + PMOD6 stub (exact items only)
DEAD_VIas = [(165.9, 82.8), (164.2, 84.1), (160.7, 91.6), (163.9, 88.9), (165.6, 86.4)]
DEAD_TRK = [(161.3, 88.6)]
removed = 0
for t in list(b.GetTracks()):
    p = t.GetPosition()
    px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    if t.GetClass() == "PCB_VIA":
        if any(abs(px - x) < 0.15 and abs(py - y) < 0.15 for x, y in DEAD_VIas):
            b.RemoveNative(t); removed += 1
    else:
        for end in (t.GetStart(), t.GetEnd()):
            ex, ey = pcbnew.ToMM(end.x), pcbnew.ToMM(end.y)
            if any(abs(ex - x) < 0.1 and abs(ey - y) < 0.1 for x, y in DEAD_TRK):
                b.RemoveNative(t); removed += 1
                break
print("removed dead items:", removed)

# ---- tracks
def net(name):
    return b.FindNet(name)

def route(netname, layer, pts, width=0.25):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c))
        t.SetWidth(FMM(width)); t.SetLayer(layer)
        t.SetNet(net(netname))
        b.Add(t)

def via(netname, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y))
    v.SetDrill(FMM(0.3)); v.SetWidth(FMM(0.6))
    v.SetNet(net(netname))
    b.Add(v)

# SCK repair: U1.6 -> U2.6 through freed PSRAM-B area
route("PMOD4", F, [(166.31, 79.53), (167.3, 79.53), (167.3, 90.6),
                   (160.06, 90.6), (160.06, 89.42)])
# +3.3V feed to L1.1
route("+3.3V", F, [(171.54, 75.9), (169.21, 75.9), (169.21, 77.02)])
# filtered rail: L1.2 -> C8.1; trunk below C8 to C9.1; drops to U4.5/U4.1
route("AUDIO_VCCA", F, [(173.66, 75.9), (175.45, 75.9)])
route("AUDIO_VCCA", F, [(173.66, 75.9), (173.66, 77.3), (178.8, 77.3),
                        (178.8, 75.9)])
route("AUDIO_VCCA", F, [(173.66, 77.3), (173.66, 78.75), (173.64, 78.75)])
route("AUDIO_VCCA", F, [(171.96, 78.75), (173.64, 78.75)])
# PMOD8: J2.6 (TH) -> B.Cu -> via -> U4.2
route("PMOD8", B, [(154.3, 88.58), (155.9, 90.18), (155.9, 93.8),
                   (170.9, 93.8), (170.9, 80.2)])
via("PMOD8", 170.9, 80.2)
route("PMOD8", F, [(170.9, 80.2), (170.9, 79.4), (171.96, 79.4)])
# buffer out -> R4.1
route("AUDIO_BUF", F, [(173.64, 80.05), (174.5, 80.05), (174.5, 79.4),
                       (175.4, 79.4)])
# N1: R4.2 -> C10.1; channel down; west leg to C11.1; east leg to R5.2
route("AUDIO_N1", F, [(177.0, 79.4), (178.7, 79.4)])
route("AUDIO_N1", F, [(177.85, 79.4), (177.85, 81.0), (171.6, 81.0),
                      (171.6, 82.3)])
route("AUDIO_N1", F, [(177.85, 81.0), (180.2, 81.0), (180.2, 82.3),
                      (179.2, 82.3)])
# N2 trunk y83.7: R5.1 drop, west to C13.2 drop; C12.1 spur; RV1 wiper via
# a west detour that crosses nothing
route("AUDIO_N2", F, [(177.6, 82.3), (177.6, 83.7), (171.0, 83.7)])
route("AUDIO_N2", F, [(174.6, 83.7), (174.6, 82.3)])
route("AUDIO_N2", F, [(171.85, 83.7), (171.85, 85.2)])
route("AUDIO_N2", F, [(171.0, 83.7), (171.0, 87.66), (175.0, 87.66)])
# OUT: C13.1 -> R6.1 straight; south T then east corridor to jack pads
route("AUDIO_OUT", F, [(173.75, 85.2), (175.6, 85.2)])
route("AUDIO_OUT", F, [(175.2, 85.2), (175.2, 86.4), (188.62, 86.4),
                       (188.62, 88.45)])
route("AUDIO_OUT", F, [(183.62, 86.4), (183.62, 80.95)])
# GND stitching vias in the extension
for (x, y) in [(171.4, 94.0), (181.0, 76.0), (182.5, 91.5), (194.5, 93.5)]:
    via("GND", x, y)

# ---- GND pours over the extension, both layers (clone existing GND zone)
gz = None
for z in b.Zones():
    if z.GetNetname() == "GND":
        gz = z
        break
for layer in (F, B):
    z2 = gz.Duplicate()
    z2 = pcbnew.Cast_to_ZONE(z2) if hasattr(pcbnew, "Cast_to_ZONE") else z2
    z2.SetLayer(layer)
    z2.SetAssignedPriority(0)
    o = z2.Outline()
    o.RemoveAllContours()
    o.NewOutline()
    for (x, y) in [(170.6, 74.7), (196.0, 74.7), (196.0, 94.7), (170.6, 94.7)]:
        o.Append(FMM(x), FMM(y))
    b.Add(z2)
print("zones added")

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("saved")
