"""Rebuild all footprint 3D model entries (SWIG in-place edits don't persist;
clear + push_back does). Applies path mapping and RV1/J3 alignment."""
import pcbnew

b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
D = "${KICAD10_3DMODEL_DIR}"
EXACT = {
    "U1": D + "/Package_SO.3dshapes/SOIC-8_5.3x5.3mm_P1.27mm.step",
    "U2": D + "/Package_SO.3dshapes/SOIC-8_3.9x4.9mm_P1.27mm.step",
    # exact LCSC C2884998 model fetched via easyeda2kicad
    "J3": "${KIPRJMOD}/easyeda/ea.3dshapes/AUDIO-SMD_PJ-320B_C2884998.step",
}
TUNE = {  # ref: (rx, ry, rz, ox, oy, oz)  -- FINAL calibrated values
    "RV1": (-90, 0, 0, 0, 0, -0.3),
    "J3":  (0, 0, 270, -0.6, 0, 3.3),
}
import sys
if len(sys.argv) > 1:
    a = sys.argv[1:]
    TUNE[a[0]] = tuple(float(x) for x in a[1:7])

for fp in b.GetFootprints():
    ref = fp.GetReference()
    models = fp.Models()
    if models.empty():
        continue
    specs = []
    for m in models:
        fn = m.m_Filename
        if ref in EXACT:
            fn = EXACT[ref]
        fn = fn.replace("KICAD6_3DMODEL_DIR", "KICAD10_3DMODEL_DIR") \
               .replace("KICAD8_3DMODEL_DIR", "KICAD10_3DMODEL_DIR")
        if fn.endswith(".wrl"):
            fn = fn[:-4] + ".step"
        rot = TUNE.get(ref, (m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z,
                             m.m_Offset.x, m.m_Offset.y, m.m_Offset.z))
        specs.append((fn, rot))
    models.clear()
    for (fn, (rx, ry, rz, ox, oy, oz)) in specs:
        nm = pcbnew.FP_3DMODEL()
        nm.m_Filename = fn
        nm.m_Rotation = pcbnew.VECTOR3D(rx, ry, rz)
        nm.m_Offset = pcbnew.VECTOR3D(ox, oy, oz)
        models.push_back(nm)
        if ref in TUNE or ref in EXACT:
            print(ref, fn.split("/")[-1], "rot", (rx, ry, rz), "off", (ox, oy, oz))
pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
