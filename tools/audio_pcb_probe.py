import pcbnew
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\refs\tt-audio-pmod\tt-audio-pmod.kicad_pcb")
bb = b.GetBoardEdgesBoundingBox()
print(f"board bbox: ({mm(bb.GetLeft()):.2f},{mm(bb.GetTop()):.2f}) to ({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")
for fp in b.GetFootprints():
    if fp.GetReference() in ("J5", "RV1", "U1", "J1"):
        p = fp.GetPosition()
        print(f"{fp.GetReference()} {fp.GetFPID().GetLibItemName()} at ({mm(p.x):.2f},{mm(p.y):.2f}) rot {fp.GetOrientationDegrees():.0f} layer {fp.GetLayerName()}")
        if fp.GetReference() == "J5":
            fbb = fp.GetBoundingBox(False)
            print(f"   J5 bbox: ({mm(fbb.GetLeft()):.2f},{mm(fbb.GetTop()):.2f}) to ({mm(fbb.GetRight()):.2f},{mm(fbb.GetBottom()):.2f})")
