# run.py — RTL simulation of the bring-up harness via cocotb's Python runner.
#   python run.py            (runs both orientations: mapping A and B)
# Same Windows-friendly pattern as tt-riscv/test/run.py.
from pathlib import Path

from cocotb_tools.runner import get_runner

TEST_DIR = Path(__file__).parent
FPGA_DIR = TEST_DIR.parent

SOURCES = [
    FPGA_DIR / "spi_byte.sv",
    FPGA_DIR / "uart_tx.sv",
    FPGA_DIR / "bringup_top.sv",
    TEST_DIR / "tb.sv",
]


def main():
    runner = get_runner("icarus")
    runner.build(
        sources=SOURCES,
        hdl_toplevel="tb",
        build_dir=TEST_DIR / "sim_build",
        build_args=["-g2012"],
        timescale=("1ns", "1ps"),
    )
    for mapb in (0, 1):
        runner.test(
            hdl_toplevel="tb",
            test_module="test_bringup",
            test_dir=TEST_DIR,
            plusargs=[f"+MAPB={mapb}"],
            results_xml=f"results_map{'ba'[mapb == 0]}.xml",
        )


if __name__ == "__main__":
    main()
