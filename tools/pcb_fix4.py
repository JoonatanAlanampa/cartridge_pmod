"""Fix round 4: SCK onto B.Cu via PMOD4's own corridor, undo F.Cu corridor
(restores +3.3V pour), row3/RV1 final positions, one continuous B GND zone."""
import pcbnew

PCB = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb"
FMM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(PCB)
F, B = pcbnew.F_Cu, pcbnew.B_Cu

# ---- delete: old SCK F corridor + row3-dependent audio segs
DEL_SEGS = [
    (146.97, 86.03, 148.30, 86.03), (148.30, 86.03, 148.30, 84.85),
    (148.30, 84.85, 155.90, 84.85), (155.90, 84.85, 155.90, 85.70),
    (155.90, 85.70, 164.50, 85.70), (164.50, 85.70, 164.50, 80.10),
    (164.50, 80.10, 165.20, 80.10), (165.20, 80.10, 165.20, 79.53),
    (165.20, 79.53, 166.31, 79.53),
    (171.85, 84.10, 171.85, 85.60),                      # C13.2 feeder
    (171.00, 84.10, 171.00, 87.66), (171.00, 87.66, 175.00, 87.66),  # wiper
    (173.75, 85.60, 175.60, 85.60), (175.20, 85.60, 175.20, 86.60),  # OUT row3
]

def close(a, b_, tol=0.05):
    return abs(a - b_) < tol

removed = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        continue
    s, e = t.GetStart(), t.GetEnd()
    sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
    for (x1, y1, x2, y2) in DEL_SEGS:
        if (close(sx, x1) and close(sy, y1) and close(ex, x2) and close(ey, y2)) or \
           (close(sx, x2) and close(sy, y2) and close(ex, x1) and close(ey, y1)):
            b.RemoveNative(t); removed += 1
            break
print("removed", removed)

# ---- moves
for ref, (x, y, rot) in {"C13": (172.8, 85.5, 180), "R6": (176.4, 85.5, 0),
                         "RV1": (175.0, 90.7, 0)}.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)

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

# SCK: tap PMOD4 B.Cu east end, corridor between PMOD8-B and PMOD2-B diag,
# via up at (164.9,87.5), F.Cu north past U1.5's west edge into U1.6
route("PMOD4", B, [(159.8, 87.1), (164.5, 87.1), (164.9, 87.5)])
via("PMOD4", 164.9, 87.5)
route("PMOD4", F, [(164.9, 87.5), (164.9, 80.1), (165.2, 80.1),
                   (165.2, 79.53), (166.31, 79.53)])
# row3-dependent audio nets at y85.5 / RV1 at 90.7
route("AUDIO_N2", F, [(171.85, 84.1), (171.85, 85.5)])
route("AUDIO_N2", F, [(171.0, 84.1), (171.0, 88.16), (175.0, 88.16)])
route("AUDIO_OUT", F, [(173.75, 85.5), (175.6, 85.5)])
route("AUDIO_OUT", F, [(175.2, 85.5), (175.2, 86.6)])
# R6.2 ground stub + via (pour can't give it two spokes)
route("GND", F, [(177.2, 85.5), (178.35, 85.5)])
via("GND", 178.35, 85.5)

# ---- zones: kill my B-ext zone, stretch the original B GND zone to x=196
for z in list(b.Zones()):
    if z.GetNetname() == "GND" and z.GetLayer() == B and \
       mm(z.GetBoundingBox().GetLeft()) > 169.0:
        b.RemoveNative(z)
        print("killed B ext zone")
for z in b.Zones():
    if z.GetNetname() == "GND" and z.GetLayer() == B:
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for (x, y) in [(139.2, 74.5), (196.0, 74.5), (196.0, 95.0), (139.2, 95.0)]:
            o.Append(FMM(x), FMM(y))
        print("stretched main B GND zone")
        break

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("saved")
