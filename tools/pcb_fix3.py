"""Fix round 3: restore outline lines, rotate R4, respace rows 2/3,
reroute SCK via J1.4 tap, reuse original PMOD8 corridor, GND stub vias,
rebuild extension zones. All coordinates verified against probe3 output."""
import pcbnew

PCB = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb"
FMM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
b = pcbnew.LoadBoard(PCB)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
mm = pcbnew.ToMM

# ---- 1. restore missing top/bottom outline lines
def add_line(p1, p2, layer=pcbnew.Edge_Cuts, w=0.1):
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(V(*p1)); sh.SetEnd(V(*p2))
    sh.SetLayer(layer); sh.SetWidth(FMM(w))
    b.Add(sh)

add_line((141.0, 74.70), (195.0, 74.71))
add_line((141.0, 94.70), (195.0, 94.70))

# ---- 2. delete my bad tracks
DEL_SEGS = [  # (x1,y1,x2,y2) either direction
    (166.31, 79.53, 167.30, 79.53), (167.30, 79.53, 167.30, 90.60),
    (167.30, 90.60, 160.06, 90.60), (160.06, 90.60, 160.06, 89.42),
    (154.30, 88.58, 155.90, 90.18), (155.90, 90.18, 155.90, 93.80),
    (155.90, 93.80, 170.90, 93.80), (170.90, 93.80, 170.90, 80.20),
    (170.90, 80.20, 170.90, 79.40), (170.90, 79.40, 171.96, 79.40),
]
DEL_VIas = [(170.90, 80.20), (171.40, 94.00)]
DEL_NETS = {"AUDIO_BUF", "AUDIO_N1", "AUDIO_N2", "AUDIO_OUT"}

def close(a, b_, tol=0.05):
    return abs(a - b_) < tol

removed = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        if any(close(mm(p.x), x) and close(mm(p.y), y) for x, y in DEL_VIas):
            b.RemoveNative(t); removed += 1
        continue
    if t.GetNetname() in DEL_NETS:
        b.RemoveNative(t); removed += 1
        continue
    s, e = t.GetStart(), t.GetEnd()
    sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
    for (x1, y1, x2, y2) in DEL_SEGS:
        if (close(sx, x1) and close(sy, y1) and close(ex, x2) and close(ey, y2)) or \
           (close(sx, x2) and close(sy, y2) and close(ex, x1) and close(ey, y1)):
            b.RemoveNative(t); removed += 1
            break
print("removed", removed, "items")

# ---- 3. placement updates
MOVES = {
    "R4":  (176.2, 79.4, 180),   # flip so pad2(BUF) faces the buffer
    "C11": (172.4, 82.6, 0), "C12": (175.4, 82.6, 0), "R5": (178.4, 82.6, 0),
    "C13": (172.8, 85.6, 180), "R6": (176.4, 85.6, 0),
}
for ref, (x, y, rot) in MOVES.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)

# ---- 4. routing
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

# SCK: tap PMOD4 at J1.4 TH pad, verified corridor to U1.6
route("PMOD4", F, [(146.97, 86.03), (148.3, 86.03), (148.3, 84.85),
                   (155.9, 84.85), (155.9, 85.7), (164.5, 85.7),
                   (164.5, 80.1), (165.2, 80.1), (165.2, 79.53),
                   (166.31, 79.53)])
# PMOD8: revive original corridor's east end with a via, F.Cu to U4.2
via("PMOD8", 165.8, 86.4)
route("PMOD8", F, [(165.8, 86.4), (170.4, 86.4), (170.4, 79.4),
                   (171.96, 79.4)])
# buffer out -> R4.2 (R4 flipped: pad2 west)
route("AUDIO_BUF", F, [(173.64, 80.05), (174.5, 80.05), (174.5, 79.4),
                       (175.4, 79.4)])
# N1
route("AUDIO_N1", F, [(177.0, 79.4), (178.7, 79.4)])
route("AUDIO_N1", F, [(177.85, 79.4), (177.85, 81.35), (171.6, 81.35),
                      (171.6, 82.6)])
route("AUDIO_N1", F, [(177.85, 81.35), (180.2, 81.35), (180.2, 82.6),
                      (179.2, 82.6)])
# N2
route("AUDIO_N2", F, [(177.6, 82.6), (177.6, 84.1), (171.0, 84.1)])
route("AUDIO_N2", F, [(174.6, 84.1), (174.6, 82.6)])
route("AUDIO_N2", F, [(171.85, 84.1), (171.85, 85.6)])
route("AUDIO_N2", F, [(171.0, 84.1), (171.0, 87.66), (175.0, 87.66)])
# OUT
route("AUDIO_OUT", F, [(173.75, 85.6), (175.6, 85.6)])
route("AUDIO_OUT", F, [(175.2, 85.6), (175.2, 86.6), (188.62, 86.6),
                       (188.62, 88.45)])
route("AUDIO_OUT", F, [(183.62, 86.6), (183.62, 80.95)])
# GND stubs + vias for pads the pour cannot reach
for (px, py, vx, vy) in [
        (177.35, 75.9, 177.35, 76.55),   # C8.2
        (180.4, 75.9, 180.4, 76.55),     # C9.2
        (171.96, 80.05, 171.96, 80.6),   # U4.3
        (173.18, 82.6, 173.18, 83.35),   # C11.2
        (176.18, 82.6, 176.18, 83.35)]:  # C12.2
    route("GND", F, [(px, py), (vx, vy)])
    via("GND", vx, vy)
via("GND", 172.2, 92.7)  # replacement stitch

# ---- 5. rebuild extension zones (B zone must not overlap old GND zone)
kill_zones = [z for z in b.Zones()
              if z.GetNetname() == "GND" and mm(z.GetBoundingBox().GetLeft()) > 169.0]
for z in kill_zones:
    b.RemoveNative(z)
print("killed", len(kill_zones), "ext zones")

gz = None
for z in b.Zones():
    if z.GetNetname() == "GND":
        gz = z
        break
for layer, x0 in ((F, 170.6), (B, 171.1)):
    z2 = gz.Duplicate()
    z2.SetLayer(layer)
    z2.SetAssignedPriority(0)
    o = z2.Outline()
    o.RemoveAllContours()
    o.NewOutline()
    for (x, y) in [(x0, 74.7), (196.0, 74.7), (196.0, 94.7), (x0, 94.7)]:
        o.Append(FMM(x), FMM(y))
    b.Add(z2)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("saved")
