# run_flasher.py — build + run only the flasher test (debug convenience).
from run import SOURCES, TEST_DIR
from cocotb_tools.runner import get_runner


def main():
    runner = get_runner("icarus")
    runner.build(
        sources=SOURCES,
        hdl_toplevel="tb",
        build_dir=TEST_DIR / "sim_build",
        build_args=["-g2012"],
        timescale=("1ns", "1ps"),
    )
    runner.test(
        hdl_toplevel="tb",
        test_module="test_flasher",
        test_dir=TEST_DIR,
        plusargs=["+MAPB=0"],
        results_xml="results_flasher.xml",
    )


if __name__ == "__main__":
    main()
