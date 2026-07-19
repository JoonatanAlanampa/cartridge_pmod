import pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
for z in b.Zones():
    if z.GetNetname() != "+3.3V":
        continue
    fill = z.GetFilledPolysList(pcbnew.F_Cu)
    print("outlines:", fill.OutlineCount())
    for i in range(fill.OutlineCount()):
        o = fill.Outline(i)
        bb = o.BBox()
        print(f"  island {i}: ({mm(bb.GetX()):.1f},{mm(bb.GetY()):.1f}) "
              f"w={mm(bb.GetWidth()):.1f} h={mm(bb.GetHeight()):.1f}")
