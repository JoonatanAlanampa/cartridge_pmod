"""Map legacy model refs to files that actually exist in KiCad 10."""
import pcbnew

b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
D = "${KICAD10_3DMODEL_DIR}"
EXACT = {
    "U1": D + "/Package_SO.3dshapes/SOIC-8_5.3x5.3mm_P1.27mm.step",
    "U2": D + "/Package_SO.3dshapes/SOIC-8_3.9x4.9mm_P1.27mm.step",
}
for fp in b.GetFootprints():
    ref = fp.GetReference()
    for m in fp.Models():
        old = m.m_Filename
        if ref in EXACT:
            m.m_Filename = EXACT[ref]
        elif old.endswith(".wrl"):
            m.m_Filename = old[:-4] + ".step"
        if m.m_Filename != old:
            print(f"{ref:5s} -> {m.m_Filename.split('/')[-1]}")
pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
