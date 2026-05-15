# SPDX-License-Identifier: Apache-2.0

import argparse
import os
from pathlib import Path

from cocotb_tools.check_results import get_results
from cocotb_tools.runner import get_runner


REPO_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = REPO_DIR / "test"
SRC_DIR = REPO_DIR / "src"
VENV_DIR = REPO_DIR / ".venv"


def _prepend_path(*paths):
    os.environ["PATH"] = os.pathsep.join(str(path) for path in paths) + os.pathsep + os.environ["PATH"]


def _configure_windows_environment():
    oss_dir = Path(os.environ.get("OSS_CAD_SUITE", "C:/Progs/oss-cad-suite"))
    python_base = Path(os.environ.get("PYTHON_BASE", "C:/Progs/Python310"))

    if os.name != "nt":
        return

    _prepend_path(
        VENV_DIR / "Scripts",
        python_base,
        oss_dir / "bin",
        oss_dir / "lib",
    )

    os.environ.setdefault("PYTHONPATH", str(VENV_DIR / "Lib" / "site-packages"))
    os.environ.setdefault("LIBPYTHON_LOC", str(python_base / "python310.dll"))


def main():
    parser = argparse.ArgumentParser(description="Run ChipSynth cocotb simulations.")
    parser.add_argument(
        "target",
        nargs="?",
        default="test",
        choices=("test", "render-wav"),
        help="Simulation target to run.",
    )
    args = parser.parse_args()

    _configure_windows_environment()

    test_module = "render_wav" if args.target == "render-wav" else "test"
    build_dir = TEST_DIR / "sim_build" / "runner"

    if args.target == "render-wav":
        os.environ.setdefault("AUDIO_SEQUENCE", str(TEST_DIR / "audio_sequence.json"))
        os.environ.setdefault("AUDIO_WAV", str(TEST_DIR / "chipsynth_render.wav"))
        os.environ.setdefault("SIM_CLOCK_HZ", "196608")
        os.environ.setdefault("AUDIO_SAMPLE_RATE", "48000")

    runner = get_runner(os.environ.get("SIM", "icarus"))
    runner.build(
        sources=[SRC_DIR / "synth_divider.v", SRC_DIR / "project.v", TEST_DIR / "tb.v"],
        includes=[SRC_DIR],
        hdl_toplevel="tb",
        build_args=["-g2012"],
        build_dir=build_dir,
        always=True,
    )
    results_xml = TEST_DIR / "results.xml"
    runner.test(
        hdl_toplevel="tb",
        hdl_toplevel_lang="verilog",
        test_module=test_module,
        build_dir=build_dir,
        test_dir=TEST_DIR,
        results_xml=str(results_xml),
    )

    tests, failures = get_results(results_xml)
    if failures:
        raise SystemExit(f"{failures} of {tests} cocotb tests failed")


if __name__ == "__main__":
    main()
