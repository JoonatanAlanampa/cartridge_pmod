import pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
for d in b.GetDrawings():
    if d.GetLayerName() == "B.Silkscreen" and d.GetClass() == "PCB_SHAPE" \
       and d.GetShape() == pcbnew.SHAPE_T_CIRCLE:
        print("circle r =", round(mm(d.GetRadius()), 3),
              "filled" if d.IsSolidFill() else "outline")
for d in b.GetDrawings():
    if d.GetClass() in ("PCB_TEXT", "PCB_FIELD") and hasattr(d, "GetText") \
       and ("AUDIO" in d.GetText() or "PSRAM" in d.GetText()):
        print("text:", repr(d.GetText()), d.GetLayerName())
