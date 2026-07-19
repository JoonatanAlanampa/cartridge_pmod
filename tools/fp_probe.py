import pcbnew
mm = pcbnew.ToMM
STD = r"C:\Users\Joonatan Alanampa\AppData\Local\Programs\KiCad\10.0\share\kicad\footprints"
PRJ = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge"
targets = [
    (STD + r"\Package_TO_SOT_SMD.pretty", "SOT-353_SC-70-5"),
    (STD + r"\Inductor_SMD.pretty", "L_0805_2012Metric"),
    (PRJ + r"\LCSC.pretty", "TRIM_3362P-1-102"),
    (PRJ + r"\LCSC.pretty", "BOOMELE_PJ-320B"),
]
for lib, name in targets:
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        print(f"{name}: LOAD FAILED from {lib}")
        continue
    bb = fp.GetBoundingBox(False)
    print(f"{name}: bbox {mm(bb.GetWidth()):.1f} x {mm(bb.GetHeight()):.1f} mm")
    for pad in fp.Pads():
        p = pad.GetPosition()
        print(f"   pad '{pad.GetNumber()}' at ({mm(p.x):.2f},{mm(p.y):.2f}) "
              f"size {mm(pad.GetSizeX()):.2f}x{mm(pad.GetSizeY()):.2f} "
              f"{'TH' if pad.HasHole() else 'SMD'}")
