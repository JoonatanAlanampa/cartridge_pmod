"""Fix round 5: SCK via/snake clearances, +3.3V zone west of audio feed,
delete dangling stub, proper refill."""
import pcbnew

PCB = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb"
FMM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(PCB)
F, B = pcbnew.F_Cu, pcbnew.B_Cu

DEL_SEGS = [
    (164.50, 87.10, 164.90, 87.50),
    (164.90, 87.50, 164.90, 80.10), (164.90, 80.10, 165.20, 80.10),
    (165.20, 80.10, 165.20, 79.53),
    (168.84, 77.02, 169.96, 77.02),   # dangling +3.3V stub (old U3 feed)
]
DEL_VIas = [(164.90, 87.50)]

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

def net(name):
    return b.FindNet(name)

def route(netname, layer, pts, width=0.25):
    for a, c in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(*a)); t.SetEnd(V(*c))
        t.SetWidth(FMM(width)); t.SetLayer(layer)
        t.SetNet(net(netname))
        b.Add(t)

route("PMOD4", B, [(164.5, 87.1), (164.75, 87.35)])
v = pcbnew.PCB_VIA(b)
v.SetPosition(V(164.75, 87.35))
v.SetDrill(FMM(0.3)); v.SetWidth(FMM(0.6))
v.SetNet(net("PMOD4"))
b.Add(v)
route("PMOD4", F, [(164.75, 87.35), (164.75, 83.15), (165.25, 83.15),
                   (165.25, 81.5), (165.05, 81.5), (165.05, 79.9),
                   (165.2, 79.9), (165.2, 79.53)])

# +3.3V F zone: pull right edge to x=169.0 (east side is explicitly track-fed)
for z in b.Zones():
    if z.GetNetname() == "+3.3V":
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for (x, y) in [(140.4, 75.9), (169.0, 75.9), (169.0, 95.1), (140.4, 95.1)]:
            o.Append(FMM(x), FMM(y))
        print("+3.3V zone right edge -> 169.0")
        break

b.BuildConnectivity()
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("saved")
