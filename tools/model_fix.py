"""Fix 3D model references: legacy KICAD6/8 path vars -> KICAD10, and attach
the vendored STEP models to J3 (jack) and RV1 (trim pot)."""
import pcbnew

b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

for fp in b.GetFootprints():
    for m in fp.Models():
        old = m.m_Filename
        new = old.replace("KICAD6_3DMODEL_DIR", "KICAD10_3DMODEL_DIR") \
                 .replace("KICAD8_3DMODEL_DIR", "KICAD10_3DMODEL_DIR")
        if new != old:
            m.m_Filename = new
            print(f"{fp.GetReference():5s} -> KICAD10 var")

ADD = {
    "J3":  "${KIPRJMOD}/LCSC.3dshapes/PJ-320B--3DModel-STEP-56544.STEP",
    "RV1": "${KIPRJMOD}/LCSC.3dshapes/3362P-1-201LF.step",
}
for ref, path in ADD.items():
    fp = b.FindFootprintByReference(ref)
    if fp.Models().empty():
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = path
        fp.Models().push_back(m)
        print(f"{ref}: model attached")

pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
