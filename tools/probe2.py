import pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

print("== zones ==")
for z in b.Zones():
    bbz = z.GetBoundingBox()
    layers = [b.GetLayerName(l) for l in z.GetLayerSet().Seq()]
    print(f"  net={z.GetNetname()} layers={layers} prio={z.GetAssignedPriority()} "
          f"bbox=({mm(bbz.GetLeft()):.1f},{mm(bbz.GetTop()):.1f})-({mm(bbz.GetRight()):.1f},{mm(bbz.GetBottom()):.1f})")

print("== pads of interest ==")
for ref in ("U1", "U2", "C1", "C2", "R1", "J2", "J1"):
    fp = b.FindFootprintByReference(ref)
    for pad in fp.Pads():
        p = pad.GetPosition()
        print(f"  {ref}.{pad.GetNumber()} [{pad.GetNetname()}] at ({mm(p.x):.2f},{mm(p.y):.2f})")
