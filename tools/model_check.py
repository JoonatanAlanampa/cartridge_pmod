import pcbnew
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
for fp in b.GetFootprints():
    models = fp.Models()
    if models.empty():
        print(f"{fp.GetReference():5s} NO MODEL   ({fp.GetFPID().GetLibItemName()})")
    else:
        for m in models:
            print(f"{fp.GetReference():5s} {m.m_Filename}")
