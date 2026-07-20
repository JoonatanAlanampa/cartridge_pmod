# test_bringup.py — decode the UART report and check every test line.
# The +MAPB plusarg (read by tb.sv to wire the cartridge flipped) also tells
# this test which mapping letter the report must claim.
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer

from uart_util import UartRx


@cocotb.test(timeout_time=60, timeout_unit="ms")
async def bringup_report(dut):
    mapb = int(cocotb.plusargs.get("MAPB", 0))
    expect_map = "B" if mapb else "A"

    cocotb.start_soon(Clock(dut.clk, 40, "ns").start())
    rx = UartRx(dut)

    lines = []
    while True:
        line = await rx.line(timeout_ms=40)
        if line:
            lines.append(line)
            dut._log.info("UART: %s", line)
        if line == "DONE":
            break

    report = {l.split()[0]: l for l in lines if l}
    assert lines[0] == "CARTRIDGE-PMOD BRINGUP", lines
    assert report["MAP"] == f"MAP {expect_map}", report["MAP"]
    assert report["FLASH"] == "FLASH EF4018 PASS", report["FLASH"]
    assert report["PSRAM"] == "PSRAM 0D5D PASS", report["PSRAM"]
    assert report["MEM"] == "MEM PASS", report["MEM"]
    assert report["FLASH@0"] == "FLASH@0 DEADBEEF", report["FLASH@0"]

    led = int(dut.led.value)
    assert led & 0b0000_1110 == 0b0000_1110, "pass LEDs"
    assert (led >> 6) & 1 == 0, "fail LED must be off"
    assert ((led >> 4) & 1) == mapb, "mapping LED"

    # audio: enabled after DONE — the pin (bit 0 of gn in map A, gp in map B)
    # must actually toggle
    aud = dut.gn if mapb == 0 else dut.gp
    seen = set()
    for _ in range(2000):
        await Timer(100, "ns")
        seen.add(int(aud.value) & 1)
        if len(seen) == 2:
            break
    assert seen == {0, 1}, f"audio pin not toggling, saw {seen}"
