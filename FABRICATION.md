# Fabrication export guide (JLCPCB, PCB + SMT assembly)

Target: 5 boards, assembled front side, ~€20–30 + shipping. Everything below
was verified against this project with KiCad 10.0.4 on Windows.

## Pre-flight (already done for v0.1, re-check after any edit)

1. ERC on the schematic: 0 errors
   (`kicad-cli sch erc --severity-error cartridge-pmod.kicad_sch`).
2. DRC on the board: 0 unconnected; only the 23 known-ignorable errors
   (22 CONFIG-jumper cut-trace + 1 upstream starved-thermal on R1)
   (`kicad-cli pcb drc cartridge-pmod.kicad_pcb`).
3. Zones refilled (open PCB in GUI, press **B**, save — or any tools/ script
   that ends with `ZONE_FILLER`).
4. Supplier fields present **on the board**, not only the schematic: the
   Fabrication Toolkit reads footprint fields, so `LCSC Part` must be pushed
   across with Tools → Update PCB from Schematic (F8, "update fields" ticked).
   Without it the audio-section LCSC numbers export blank. Fixed 2026-07-20.
5. J1 (hand-soldered Pmod header) and J2 (CONFIG solder jumpers) are marked
   DNP, so they drop out of both the BOM and the placement file.
6. Board committed + pushed.

## Option A — Fabrication Toolkit plugin (recommended, one click)

1. Open KiCad → **Plugin and Content Manager** → install **Fabrication
   Toolkit** (by bennymeg; made specifically for JLCPCB).
2. Open the PCB editor, click the Fabrication Toolkit icon in the toolbar.
3. It writes a `production/` folder containing:
   - `gerbers.zip` (all copper/mask/silk/edge layers + drill files)
   - `bom.csv` (grouped by value+footprint, with the **LCSC Part** field)
   - `positions.csv` (component placement / CPL, JLC-rotation-corrected)
4. Upload to jlcpcb.com — see "Ordering" below.

## Option B — pure kicad-cli (no GUI, scriptable)

Run from the project directory
(`$cli = "$env:LOCALAPPDATA\Programs\KiCad\10.0\bin\kicad-cli.exe"`):

```powershell
# gerbers (copper, mask, silk both sides, board edge)
& $cli pcb export gerbers --output fab/ `
    --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts `
    cartridge-pmod.kicad_pcb
# drill files (Excellon, PTH+NPTH merged is fine for JLC)
& $cli pcb export drill --output fab/ --format excellon `
    --excellon-units mm cartridge-pmod.kicad_pcb
# placement file, front side, CSV in mm
& $cli pcb export pos --output fab/positions.csv --format csv --units mm `
    --side front cartridge-pmod.kicad_pcb
# BOM with LCSC numbers
& $cli sch export bom --output fab/bom.csv `
    --fields "Reference,Value,Footprint,${'$'}{QUANTITY},LCSC Part,MPN" `
    cartridge-pmod.kicad_sch
# zip the gerbers + drill for upload
Compress-Archive fab/*.gbr, fab/*.drl fab/gerbers.zip
```

Caveat vs Option A: JLC wants specific CPL column names
(Designator, Mid X, Mid Y, Layer, Rotation) and some footprints need
rotation offsets — the Fabrication Toolkit handles both automatically,
kicad-cli output may need manual column renaming and rotation fixes in the
JLC preview. Prefer Option A for ordering; use Option B for CI/checks.

## Ordering at jlcpcb.com

1. **Add gerber file** → upload `gerbers.zip`. Check the rendered preview
   (board outline 56.3 x 20.1 mm, both silk sides, pearto visible on back).
2. PCB options: 2 layers, 1.6 mm, HASL(lead-free ok), any color, qty 5.
   Leave everything else default. "Remove Order Number" → "Specify a
   location" is NOT set up on this board — accept the printed order number
   or pay the small fee to remove it.
3. Enable **PCB Assembly**: Economic, top side, qty 2 or 5.
4. Upload `bom.csv` and `positions.csv`.
5. Parts matching page — check each line:
   - Audio section parts all carry explicit LCSC numbers
     (U4 C842506, L1 C2941578, C8 C15850, C9/C10/C12 C14663, C11 C1622,
     R4 C22787, R5 C23140, R6 C23179, RV1 C124581, J3 C2884998, J1 C60565).
   - Memory section (U1 W25Q128JVSIM, U2 APS6404L-3SQR-SN, 0402 R/C) has
     MPNs but no LCSC field — JLC usually auto-matches by MPN; verify the
     match, or search the LCSC number manually and paste it in.
   - **Do-not-place**: J2 CONFIG header is a solder-jumper pattern +
     optional pin header — confirm whether a physical header is wanted;
     if not, mark J2 DNP (the jumper pads still work with solder blobs).
6. Placement preview: verify U1/U2/U4 pin-1 orientation and RV1/J3 outline
   vs pads (these are the rotation-risk parts). Fix rotations in the JLC
   editor if a part renders rotated.
7. THT parts (Pmod header J1, jack J3 has TH anchors but is SMT-pad
   soldered; the header is NOT assembled) — J1 is hand-soldered at home:
   that is what the Pinecil is for.
8. Order. Economic assembly typically adds ~1 week.

## After ordering

- Tag the repo: `git tag fab-v0.1 && git push --tags`.
- First power-up checklist: continuity 3V3-GND (multimeter, before first
  plug-in!), then flash/PSRAM ID read via TT demo board or ULX3S harness,
  then audio: drive uio7 with a sigma-delta/PWM tone >= 200 kHz carrier.
