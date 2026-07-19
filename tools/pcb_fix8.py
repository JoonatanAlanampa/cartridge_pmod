"""Fix round 8: PMOD8 exit clear of N2 branch; +3.3V zone local clearance."""
import pcbnew

FMM = pcbnew.FromMM
mm = pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
F, B = pcbnew.F_Cu, pcbnew.B_Cu

DEL_SEGS = [(168.45, 86.4, 170.7, 86.4), (170.7, 86.4, 170.7, 79.4),
            (170.7, 79.4, 171.96, 79.4)]
DEL_VIas = [(170.7, 86.4)]

def close(a, b_, tol=0.05):
    return abs(a - b_) < tol

removed = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        if any(close(mm(p.x), x) and close(mm(p.y), y) for x, y in DEL_VIas):
            b.RemoveNative(t); removed += 1
        continue
    s, e = t.GetStart(), t.GetEnd()
    sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
    for (x1, y1, x2, y2) in DEL_SEGS:
        if (close(sx, x1) and close(sy, y1) and close(ex, x2) and close(ey, y2)) or \
           (close(sx, x2) and close(sy, y2) and close(ex, x1) and close(ey, y1)):
            b.RemoveNative(t); removed += 1
            break
print("removed", removed)

def route(nn, layer, pts):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c))
        t.SetWidth(FMM(0.25)); t.SetLayer(layer)
        t.SetNet(b.FindNet(nn))
        b.Add(t)

def via(nn, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y))
    v.SetDrill(FMM(0.3)); v.SetWidth(FMM(0.6))
    v.SetNet(b.FindNet(nn))
    b.Add(v)

route("PMOD8", B, [(168.45, 86.4), (169.3, 86.4), (169.3, 83.5),
                   (170.5, 83.5)])
via("PMOD8", 170.5, 83.5)
route("PMOD8", F, [(170.5, 83.5), (170.5, 79.4), (171.96, 79.4)])

PTS = [(140.40, 90.30), (148.70, 90.30), (150.80, 92.20), (155.60, 92.20),
       (155.60, 82.90), (157.90, 82.90), (157.90, 92.20), (168.80, 92.20),
       (168.80, 75.90), (170.10, 75.90), (170.10, 95.10), (140.40, 95.10)]
for z in b.Zones():
    if z.GetNetname() == "+3.3V":
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for (x, y) in PTS:
            o.Append(FMM(x), FMM(y))
        z.SetLocalClearance(FMM(0.25))
        print("+3.3V zone: edge 170.1, local clearance 0.25")
        break

b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
