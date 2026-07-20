#!/usr/bin/env python3
"""flash_cartridge.py — write a binary image into the Cartridge Pmod's
W25Q128 through the bring-up bitstream's UART flash-writer.

    python flash_cartridge.py COM7 hello.bin [--base 0x000000] [--no-verify]

Needs pyserial (pip install pyserial). Flash the bring-up bitstream first
(openFPGALoader -b ulx3s fpga/build/cartridge_bringup.bit), let the power-up
report finish (or just run this — it waits for the line to go quiet).

Protocol (all fields MSB first, gateware side in bringup_top.sv):
    'I'                  -> 3 bytes JEDEC ID (EF 40 18)
    'E' + addr24         -> 4 KB sector erase, 'K' when done
    'P' + addr24 + 256B  -> page program, 'K' when done
    'R' + addr24         -> 256 bytes read back
"""
import argparse
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pyserial missing: pip install pyserial")

SECTOR = 4096
PAGE = 256


def drain(port, quiet_s=0.5):
    """Swallow the bring-up report: wait until the line is quiet."""
    port.timeout = quiet_s
    while True:
        if not port.read(4096):
            return


def expect_k(port, what, timeout_s=3.0):
    port.timeout = timeout_s
    r = port.read(1)
    if r != b"K":
        sys.exit(f"{what}: expected 'K', got {r!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", help="serial port (COM7, /dev/ttyUSB0, ...)")
    ap.add_argument("binfile")
    ap.add_argument("--base", type=lambda x: int(x, 0), default=0,
                    help="flash byte address to write at (default 0)")
    ap.add_argument("--no-verify", action="store_true")
    args = ap.parse_args()

    if args.base % SECTOR:
        sys.exit(f"--base must be {SECTOR}-aligned")

    data = open(args.binfile, "rb").read()
    if not data:
        sys.exit("empty image")
    print(f"{args.binfile}: {len(data)} bytes -> flash @0x{args.base:06X}")

    port = serial.Serial(args.port, 115200, dsrdtr=False, rtscts=False)
    port.dtr = False
    port.rts = False
    print("waiting for the bring-up report to finish...")
    drain(port)

    # handshake
    for attempt in range(3):
        port.reset_input_buffer()
        port.write(b"I")
        port.timeout = 1.0
        fid = port.read(3)
        if fid == b"\xEF\x40\x18":
            break
        print(f"  ID attempt {attempt + 1}: got {fid.hex() or 'nothing'}")
    else:
        sys.exit("no valid flash ID — is the bring-up bitstream loaded "
                 "and the cartridge plugged in / passing its tests?")
    print("flash ID OK (EF 40 18)")

    end = args.base + len(data)
    sectors = range(args.base, end, SECTOR)
    for i, s in enumerate(sectors):
        port.write(b"E" + s.to_bytes(3, "big"))
        expect_k(port, f"erase @0x{s:06X}", timeout_s=5.0)
        print(f"\rerase  {i + 1}/{len(sectors)} sectors", end="")
    print()

    npages = (len(data) + PAGE - 1) // PAGE
    for i in range(npages):
        chunk = data[i * PAGE:(i + 1) * PAGE].ljust(PAGE, b"\xFF")
        addr = args.base + i * PAGE
        port.write(b"P" + addr.to_bytes(3, "big") + chunk)
        expect_k(port, f"program @0x{addr:06X}")
        print(f"\rwrite  {i + 1}/{npages} pages", end="")
    print()

    if not args.no_verify:
        for i in range(npages):
            addr = args.base + i * PAGE
            port.write(b"R" + addr.to_bytes(3, "big"))
            port.timeout = 3.0
            rd = port.read(PAGE)
            want = data[i * PAGE:(i + 1) * PAGE].ljust(PAGE, b"\xFF")
            if rd != want:
                sys.exit(f"\nverify FAIL @0x{addr:06X}")
            print(f"\rverify {i + 1}/{npages} pages", end="")
        print()

    print(f"done: {len(data)} bytes flashed"
          + ("" if args.no_verify else " and verified"))


if __name__ == "__main__":
    main()
