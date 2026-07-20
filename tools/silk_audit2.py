"""Detail geometry around the audio caps row + CONFIG/CK area for label placement."""
import pcbnew

mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

print("-- footprint positions + courtyard bboxes, audio region --")
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref in ("C11", "C12", "C13", "R5", "R6", "U4", "R4", "C10", "RV1", "C7", "J2"):
        p = fp.GetPosition()
        bb = fp.GetBoundingBox(False)
        print(f"{ref:4s} at ({mm(p.x):.2f},{mm(p.y):.2f}) rot {fp.GetOrientationDegrees():.0f} "
              f"bbox ({mm(bb.GetLeft()):.2f},{mm(bb.GetTop()):.2f})-({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")
        for pad in fp.Pads():
            pb = pad.GetBoundingBox()
            print(f"     pad {pad.GetName()} ({mm(pb.GetLeft()):.2f},{mm(pb.GetTop()):.2f})-({mm(pb.GetRight()):.2f},{mm(pb.GetBottom()):.2f})")

print("\n-- board text bboxes (CK/B/F/A + credits) --")
for d in b.GetDrawings():
    if d.Type() == pcbnew.PCB_TEXT_T and d.GetText() in ("CK", "B", "F", "A"):
        bb = d.GetBoundingBox()
        print(f"'{d.GetText()}' bbox ({mm(bb.GetLeft()):.2f},{mm(bb.GetTop()):.2f})-({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")

print("\n-- J1 pads --")
j1 = b.FindFootprintByReference("J1")
for pad in j1.Pads():
    pb = pad.GetBoundingBox()
    print(f"J1 pad {pad.GetName()} ({mm(pb.GetLeft()):.2f},{mm(pb.GetTop()):.2f})-({mm(pb.GetRight()):.2f},{mm(pb.GetBottom()):.2f})")
