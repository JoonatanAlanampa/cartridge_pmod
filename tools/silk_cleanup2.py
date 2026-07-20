"""Silk cleanup round 2 + J1 assembly enable.

1. Delete J1's silk pin-drawing segments that cross/leave the board edge
   (18 DRC silk_edge_clearance warnings; the fab clips them anyway and the
   connector body covers the area).
2. Nudge the C11/C12/R5 label row up off C13's pads.
3. Un-hide C13 and R6 labels in clean spots.
4. Clear DNP on J1 so the Fabrication Toolkit exports it for JLC assembly
   (J2 stays DNP: solder-jumper pattern).
5. Refill zones, save.
"""
import pcbnew

FMM = pcbnew.FromMM
mm = pcbnew.ToMM
V = lambda x, y: pcbnew.VECTOR2I(FMM(x), FMM(y))
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
edges = b.GetBoardEdgesBoundingBox()
silk = (pcbnew.F_SilkS, pcbnew.B_SilkS)

# 1. J1 off-edge silk
j1 = b.FindFootprintByReference("J1")
doomed = []
for item in j1.GraphicalItems():
    if item.GetLayer() in silk and item.Type() == pcbnew.PCB_SHAPE_T:
        bb = item.GetBoundingBox()
        if (bb.GetLeft() < edges.GetLeft() or bb.GetRight() > edges.GetRight()
                or bb.GetTop() < edges.GetTop() or bb.GetBottom() > edges.GetBottom()):
            doomed.append(item)
for item in doomed:
    j1.Remove(item)
print(f"J1: removed {len(doomed)} off-edge silk segments")

# 2+3. labels
MOVES = {
    "C11": (172.40, 83.90, 0),
    "C12": (175.40, 83.90, 0),
    "R5":  (178.40, 83.90, 0),
    "C13": (169.60, 85.20, 0),
    "R6":  (178.90, 85.50, 0),
}
for ref, (x, y, rot) in MOVES.items():
    fp = b.FindFootprintByReference(ref)
    txt = fp.Reference()
    txt.SetVisible(True)
    txt.SetPosition(V(x, y))
    txt.SetTextAngleDegrees(rot)
    txt.SetTextSize(pcbnew.VECTOR2I(FMM(0.8), FMM(0.8)))
    txt.SetTextThickness(FMM(0.12))
    print(f"{ref}: label at ({x},{y})")

# sanity: new label bboxes vs every pad and board text on F.Silk
pads = [(p.GetParentFootprint().GetReference(), p.GetName(), p.GetBoundingBox())
        for fp in b.GetFootprints() for p in fp.Pads() if p.IsOnLayer(pcbnew.F_Cu)]
texts = [(d.GetText(), d.GetBoundingBox()) for d in b.GetDrawings()
         if d.Type() == pcbnew.PCB_TEXT_T and d.GetLayer() == pcbnew.F_SilkS]
clean = True
for ref in MOVES:
    tb = b.FindFootprintByReference(ref).Reference().GetBoundingBox()
    for pref, pname, pb in pads:
        if pref != ref and tb.Intersects(pb):
            print(f"  WARN {ref} label hits pad {pref}.{pname}")
            clean = False
    for ttext, obb in texts:
        if tb.Intersects(obb):
            print(f"  WARN {ref} label hits text '{ttext[:20]}'")
            clean = False
print("label placement clean" if clean else "label placement HAS WARNINGS")

# 4. J1 un-DNP
before = j1.GetAttributes()
if hasattr(j1, "SetDNP"):
    j1.SetDNP(False)
    print(f"J1: SetDNP(False), IsDNP now {j1.IsDNP()}")
else:
    j1.SetAttributes(before & ~pcbnew.FP_DNP)
    print(f"J1: attrs {before} -> {j1.GetAttributes()}")

# 5. refill + save
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(b.GetFileName(), b)
print("zones refilled, saved")
