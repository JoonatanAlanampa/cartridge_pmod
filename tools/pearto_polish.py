"""Polish: enforce min pupil size on the logo, rename stale PSRAM B CS label."""
import pcbnew

FMM = pcbnew.FromMM
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

# grow tiny filled silk circles (pupils/mouth) to fabbable size
for d in b.GetDrawings():
    if d.GetLayerName() == "B.Silkscreen" and d.GetClass() == "PCB_SHAPE" \
       and d.GetShape() == pcbnew.SHAPE_T_CIRCLE and d.IsSolidFill():
        r = mm(d.GetRadius())
        if r < 0.16:
            d.SetEnd(pcbnew.VECTOR2I(d.GetCenter().x + FMM(0.16), d.GetCenter().y))
            print(f"pupil {r:.2f} -> 0.16 mm radius")

for d in b.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and "PSRAM B" in d.GetText():
        print("renaming:", repr(d.GetText()))
        d.SetText("AUDIO")

pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
