# test_flasher.py — after the bring-up report, exercise the UART flash-writer:
# 'I' ID handshake, 'E' sector erase, 'P' page program, 'R' read-back.
# Model internals are peeked to keep sim time sane; one full 'R' round-trip
# proves the read path over the wire.
import cocotb
from cocotb.clock import Clock

from uart_util import UartRx, uart_send_byte

PAGE = [(i ^ 0xA5) & 0xFF for i in range(256)]


async def send_cmd(dut, cmd, addr=None, data=None):
    await uart_send_byte(dut, ord(cmd))
    if addr is not None:
        for b in ((addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF):
            await uart_send_byte(dut, b)
    if data is not None:
        for b in data:
            await uart_send_byte(dut, b)


@cocotb.test(timeout_time=200, timeout_unit="ms")
async def flash_writer(dut):
    cocotb.start_soon(Clock(dut.clk, 40, "ns").start())
    rx = UartRx(dut)

    while True:                                   # let the bring-up finish
        if await rx.line(timeout_ms=40) == "DONE":
            break

    # ID handshake
    dut._log.info("flasher: ID")
    await send_cmd(dut, "I")
    fid = [await rx.get() for _ in range(3)]
    assert fid == [0xEF, 0x40, 0x18], f"ID {fid}"

    # sector erase — DEADBEEF preload must vanish
    dut._log.info("flasher: erase")
    await send_cmd(dut, "E", addr=0)
    assert await rx.get(timeout_ms=200) == ord("K")
    for i in range(8):
        assert int(dut.u_flash.mem[i].value) == 0xFF, f"byte {i} not erased"

    # page program
    dut._log.info("flasher: program")
    await send_cmd(dut, "P", addr=0, data=PAGE)
    assert await rx.get(timeout_ms=200) == ord("K")
    for i in range(256):
        got = int(dut.u_flash.mem[i].value)
        assert got == PAGE[i], f"byte {i}: {got:02x} != {PAGE[i]:02x}"

    # read-back over the wire
    dut._log.info("flasher: read-back")
    await send_cmd(dut, "R", addr=0)
    rd = [await rx.get() for _ in range(256)]
    assert rd == PAGE, "read-back mismatch"

    dut._log.info("flasher: ID/erase/program/verify all good")
