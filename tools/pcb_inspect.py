"""Inspect board: outline, footprints, nets. Run with KiCad's python."""
import pcbnew

b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
mm = pcbnew.ToMM

print("== Edge.Cuts ==")
for d in b.GetDrawings():
    if d.GetLayerName() == "Edge.Cuts":
        t = d.GetShapeStr() if hasattr(d, "GetShapeStr") else type(d).__name__
        try:
            s, e = d.GetStart(), d.GetEnd()
            print(f"  {t}: ({mm(s.x):.2f},{mm(s.y):.2f}) -> ({mm(e.x):.2f},{mm(e.y):.2f})")
        except Exception:
            print(f"  {t}")

bb = b.GetBoardEdgesBoundingBox()
print(f"outline bbox: ({mm(bb.GetLeft()):.2f},{mm(bb.GetTop()):.2f}) to "
      f"({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")

print("== Footprints ==")
for fp in b.GetFootprints():
    p = fp.GetPosition()
    print(f"  {fp.GetReference():6s} {fp.GetFPID().GetLibItemName()} "
          f"at ({mm(p.x):.2f},{mm(p.y):.2f}) rot {fp.GetOrientationDegrees():.0f} "
          f"layer {fp.GetLayerName()}")

print("== Nets ==")
for code, net in b.GetNetsByNetcode().items():
    print(f"  {code}: {net.GetNetname()}")
