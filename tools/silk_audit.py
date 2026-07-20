"""Audit silk: all visible text (pos/size/bbox), footprint silk segments that
cross or leave the board outline, and text-vs-pad overlaps."""
import pcbnew

mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
edges = b.GetBoardEdgesBoundingBox()
L, R, T, B_ = edges.GetLeft(), edges.GetRight(), edges.GetTop(), edges.GetBottom()
print(f"board: ({mm(L):.2f},{mm(T):.2f})-({mm(R):.2f},{mm(B_):.2f})")

silk = (pcbnew.F_SilkS, pcbnew.B_SilkS)

print("\n-- footprint reference/value texts (visible) --")
for fp in b.GetFootprints():
    for label, txt in (("ref", fp.Reference()), ("val", fp.Value())):
        if txt.IsVisible() and txt.GetLayer() in silk:
            p = txt.GetPosition()
            bb = txt.GetBoundingBox()
            print(f"{fp.GetReference():4s} {label} '{txt.GetText()}' at ({mm(p.x):.2f},{mm(p.y):.2f}) "
                  f"rot {txt.GetTextAngleDegrees():.0f} h {mm(txt.GetTextSize().y):.2f} "
                  f"bbox ({mm(bb.GetLeft()):.2f},{mm(bb.GetTop()):.2f})-({mm(bb.GetRight()):.2f},{mm(bb.GetBottom()):.2f})")

print("\n-- board-level silk text --")
for d in b.GetDrawings():
    if d.GetLayer() in silk and d.Type() in (pcbnew.PCB_TEXT_T, pcbnew.PCB_TEXTBOX_T):
        p = d.GetPosition()
        print(f"text '{d.GetText()[:30]}' at ({mm(p.x):.2f},{mm(p.y):.2f})")

print("\n-- footprint silk shapes outside/crossing board edge --")
for fp in b.GetFootprints():
    for item in fp.GraphicalItems():
        if item.GetLayer() in silk and item.Type() == pcbnew.PCB_SHAPE_T:
            bb = item.GetBoundingBox()
            if bb.GetLeft() < L or bb.GetRight() > R or bb.GetTop() < T or bb.GetBottom() > B_:
                s, e = item.GetStart(), item.GetEnd()
                print(f"{fp.GetReference()} {item.ShowShape()} ({mm(s.x):.2f},{mm(s.y):.2f})->({mm(e.x):.2f},{mm(e.y):.2f})")

print("\n-- text bbox vs pad overlap (same side) --")
pads = [(p.GetParentFootprint().GetReference(), p.GetName(), p.GetBoundingBox(), p.IsOnLayer(pcbnew.F_Cu))
        for fp in b.GetFootprints() for p in fp.Pads()]
for fp in b.GetFootprints():
    txt = fp.Reference()
    if not (txt.IsVisible() and txt.GetLayer() in silk):
        continue
    front = txt.GetLayer() == pcbnew.F_SilkS
    tb = txt.GetBoundingBox()
    for pref, pname, pb, pfront in pads:
        if pfront != front or pref == fp.GetReference():
            continue
        if tb.Intersects(pb):
            print(f"{fp.GetReference()} ref-text overlaps pad {pref}.{pname}")
