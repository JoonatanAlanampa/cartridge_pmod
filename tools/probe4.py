import pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

def inbox(x, y, x0=155.0, y0=76.0, x1=172.0, y1=93.0):
    return x0 <= x <= x1 and y0 <= y <= y1

print("== all copper in x155-172 y76-93 ==")
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        x, y = mm(p.x), mm(p.y)
        if inbox(x, y):
            print(f"  VIA {t.GetNetname():10s} ({x:.2f},{y:.2f})")
    else:
        s, e = t.GetStart(), t.GetEnd()
        sx, sy, ex, ey = mm(s.x), mm(s.y), mm(e.x), mm(e.y)
        if inbox(sx, sy) or inbox(ex, ey):
            print(f"  TRK {t.GetNetname():10s} {b.GetLayerName(t.GetLayer()):4s} "
                  f"({sx:.2f},{sy:.2f})-({ex:.2f},{ey:.2f})")
