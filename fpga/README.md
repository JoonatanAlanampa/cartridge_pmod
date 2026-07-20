# Cartridge Pmod bring-up on the ULX3S 85F

Self-checking harness: probes the flash + PSRAM, runs a memory test, plays a
440 Hz test tone into the audio jack, and prints a verdict on the USB serial
port. Simulated against behavioral W25Q128/APS6404 models in both plug
orientations (`test/`), bitstream builds clean (898 LUTs, Fmax 113 MHz).

## Build & flash

```powershell
powershell -File fpga\synth.ps1                      # -> fpga\build\cartridge_bringup.bit
openFPGALoader -b ulx3s fpga\build\cartridge_bringup.bit
```

Simulate: `python fpga\test\run.py` (runs both plug orientations).

## First power-up checklist (per board — do steps 1-2 BEFORE plugging in!)

1. **Bare-board short check** (multimeter, cartridge alone on the bench):
   continuity between the Pmod plug's VCC (pins 6/12, the column nearest the
   board) and GND (pins 5/11) must be OPEN (a capacitor charge blip is fine,
   a hard beep is not).
2. **Plug position**: cartridge goes into the **J1 header, pins 1-12** — the
   6 columns at the END of the left female header. ULX3S silk numbers the
   pins; the cartridge's VCC/GND columns must land on pins 1/2 (3.3V) and
   3/4 (GND). Verify once with the meter: cartridge VCC pin to ULX3S 3.3V
   should beep. Which cartridge ROW lands on GP vs GN does not matter — the
   bitstream autodetects it (LED4 tells you which).
3. Flash the bitstream, open a serial terminal at **115200 8N1** on the
   ULX3S FTDI port. Report format:

   ```
   CARTRIDGE-PMOD BRINGUP
   MAP A                    <- or B; ! = flash never answered (both rows tried)
   FLASH EF4018 PASS        <- W25Q128 JEDEC ID
   PSRAM 0D5D PASS          <- APS6404 MF+KGD
   MEM PASS                 <- 2 write/read patterns + aliasing re-read
   FLASH@0 FFFFFFFF         <- first 4 flash bytes (blank chip = FF)
   DONE
   ```

4. **LEDs**: 0 heartbeat, 1 flash OK, 2 PSRAM OK, 3 mem OK, 4 mapping B,
   5 done, 6 any-fail, 7 audio on. **BTN1 re-runs** the whole sequence.
5. **Audio**: after all tests pass, a 440 Hz sine plays on the cartridge
   jack (sigma-delta through the RC + buffer chain). Headphones in, set
   level with RV1 (small screwdriver). Verifies the whole analog path.
6. If `MAP !` / all-fail: check the CONFIG jumpers on the cartridge back
   (F and A rows must be in their default state), re-seat the Pmod, check
   3.3V on the cartridge VCC pin while powered.

## What this proves / what's next

PASS here = the cartridge hardware is fully validated for the console
project: QSPI bus wiring, both memories, the audio chain, and the TT-pinout
compatibility (pins 1-7 identical to the stock QSPI Pmod).

Next steps on this same setup:
- quad-mode + clock sweep (the bring-up runs 12.5 MHz single-bit SPI)
- retarget `tt-riscv/fpga` XIP harness to these pins (needs the 1-PSRAM
  fallback — TinyRV32 as written expects two PSRAMs)
- race-the-beam console prototype (video via ULX3S GPDI while waiting for
  the Tiny VGA Pmod)

## Notes

- The APS6404 tCEM (8 us max CS-low) is respected by keeping bursts to
  4 bytes; the testbench model enforces it with a fatal assertion.
- SD2/SD3 (flash /WP, /HOLD) are actively driven high during SPI — they
  have no pull-ups on the cartridge.
- The ULX3S J1 power pins feed from the "2V5_3V3" net — stock boards ship
  it at 3.3 V; if yours was modified for 2.5 V I/O, put it back before
  plugging the cartridge.
