import pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

print("== tracks/vias on PMOD2/4/6/8 ==")
for t in b.GetTracks():
    if t.GetNetname() in ("PMOD2", "PMOD4", "PMOD6", "PMOD8"):
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            print(f"  VIA {t.GetNetname()} ({mm(p.x):.2f},{mm(p.y):.2f})")
        else:
            s, e = t.GetStart(), t.GetEnd()
            print(f"  TRK {t.GetNetname()} {b.GetLayerName(t.GetLayer())} "
                  f"({mm(s.x):.2f},{mm(s.y):.2f})-({mm(e.x):.2f},{mm(e.y):.2f})")

print("== Edge.Cuts ==")
for d in b.GetDrawings():
    if d.GetLayerName() == "Edge.Cuts":
        s, e = d.GetStart(), d.GetEnd()
        kind = d.ShowShape() if hasattr(d, "ShowShape") else "?"
        extra = ""
        if "rc" in str(kind).lower() or d.GetShape() == pcbnew.SHAPE_T_ARC:
            c = d.GetCenter()
            extra = f" center ({mm(c.x):.2f},{mm(c.y):.2f})"
        print(f"  {kind}: ({mm(s.x):.3f},{mm(s.y):.3f})-({mm(e.x):.3f},{mm(e.y):.3f}){extra}")
