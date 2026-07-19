"""Silk cleanup: place audio-part reference labels in row gaps (over masked
tracks = no violation), hide the two with no clean spot, small text size."""
import pcbnew

FMM = pcbnew.FromMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

# ref -> (x, y, rot) or None to hide
LABELS = {
    "L1":  (172.6, 77.3, 0),
    "C8":  (176.4, 77.3, 0),
    "C9":  (179.6, 77.3, 0),
    "U4":  (172.8, 81.35, 0),
    "R4":  (176.2, 81.35, 0),
    "C10": (179.5, 81.35, 0),
    "C11": (172.4, 84.15, 0),
    "C12": (175.4, 84.15, 0),
    "R5":  (178.4, 84.15, 0),
    "C13": None,
    "R6":  None,
    "RV1": (180.0, 90.7, 90),
    "J3":  (187.7, 92.3, 0),
}
for ref, spec in LABELS.items():
    fp = b.FindFootprintByReference(ref)
    txt = fp.Reference()
    if spec is None:
        txt.SetVisible(False)
        print(f"{ref}: hidden")
        continue
    x, y, rot = spec
    txt.SetVisible(True)
    txt.SetPosition(V(x, y))
    txt.SetTextAngleDegrees(rot)
    txt.SetTextSize(pcbnew.VECTOR2I(FMM(0.8), FMM(0.8)))
    txt.SetTextThickness(FMM(0.12))
    print(f"{ref}: at ({x},{y}) rot {rot}")

pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
