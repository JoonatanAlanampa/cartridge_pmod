# uart_util.py — bit-banged 115200 8N1 helpers shared by the tests.
#
# Receive side is a PERMANENT background listener (UartRx), like a real host
# UART. This matters: the gateware's reply can hit the wire ~1 us before the
# sender coroutine finishes its own stop bit (rx `valid` fires at 9.5 bit
# times), so a call-when-you-expect-a-byte receiver can attach mid-byte and
# frame on a data edge. Real FTDI/pyserial hosts listen continuously and
# never see this race — the testbench must do the same.
import cocotb
from cocotb.queue import Queue
from cocotb.triggers import FallingEdge, Timer, with_timeout

BIT_NS = 8681  # 115200 baud


class UartRx:
    """Continuous listener on dut.ftdi_rxd; received bytes queue up."""

    def __init__(self, dut):
        self.dut = dut
        self.q = Queue()
        self._task = cocotb.start_soon(self._listen())

    async def _listen(self):
        while True:
            await FallingEdge(self.dut.ftdi_rxd)     # start bit
            await Timer(BIT_NS + BIT_NS // 2, "ns")  # middle of bit 0
            val = 0
            for i in range(8):
                val |= int(self.dut.ftdi_rxd.value) << i
                await Timer(BIT_NS, "ns")
            self.q.put_nowait(val)   # we are mid-stop-bit: ready for next edge

    async def get(self, timeout_ms=100):
        return await with_timeout(self.q.get(), timeout_ms, "ms")

    async def line(self, timeout_ms=100):
        """Collect one LF-terminated line."""
        chars = []
        while True:
            ch = chr(await self.get(timeout_ms))
            if ch == "\n":
                return "".join(chars)
            if ch != "\r":
                chars.append(ch)


async def uart_send_byte(dut, val):
    """Drive one byte into the DUT's ftdi_txd input."""
    dut.ftdi_txd.value = 0                   # start
    await Timer(BIT_NS, "ns")
    for i in range(8):
        dut.ftdi_txd.value = (val >> i) & 1
        await Timer(BIT_NS, "ns")
    dut.ftdi_txd.value = 1                   # stop
    await Timer(BIT_NS, "ns")
