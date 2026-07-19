"""Fix round 6 (final): remove dead PMOD5 branch (old U3 SD2 feed),
auto-remove +3.3V pour islands, refill."""
import pcbnew

PCB = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb"
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(PCB)

DEL_SEGS = [
    (162.52, 80.40, 163.59, 80.40),
    (163.59, 80.40, 165.86, 82.68),
    (165.86, 82.68, 165.86, 82.82),
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

for z in b.Zones():
    if z.GetNetname() == "+3.3V":
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        print("island removal -> always")
        break

b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("saved")
