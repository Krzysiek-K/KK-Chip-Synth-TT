# ChipSynth testbench

This testbench uses [cocotb](https://docs.cocotb.org/en/stable/) to drive the DUT and check the outputs.
See below to get started or for more information, check the [website](https://tinytapeout.com/hdl/testing/).

## Setting up

For WAV rendering you need:

- Python 3
- GNU Make
- a Verilog simulator; `icarus` is the default here
- the Python packages in `requirements.txt`

On Windows, a good native setup is OSS CAD Suite plus a Python virtual
environment:

```powershell
# Run this in each new terminal.
. C:\Progs\oss-cad-suite\environment.ps1

py -3 -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you prefer WSL/Ubuntu:

```sh
sudo apt update
sudo apt install -y make python3-venv python3-pip iverilog gtkwave
python3 -m venv ../.venv
. ../.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## How to run

To run the RTL simulation:

```sh
make -B
```

On native Windows, the cocotb Python runner avoids MSYS path conversion issues
with some `make.exe` builds:

```powershell
.\.venv\Scripts\python.exe test\run_cocotb.py
```

To render a 48 kHz mono WAV from a timed register-write sequence:

```sh
make render-wav
```

Native Windows equivalent:

```powershell
.\.venv\Scripts\python.exe test\run_cocotb.py render-wav
```

The default render reads `audio_sequence.json` and writes
`chipsynth_render.wav`. You can override these without editing the Makefile:

```sh
AUDIO_SEQUENCE=my_sequence.json AUDIO_WAV=my_render.wav make render-wav
```

In PowerShell, set overrides like this:

```powershell
$env:AUDIO_SEQUENCE = "my_sequence.json"
$env:AUDIO_WAV = "my_render.wav"
make render-wav
```

The default WAV helper uses a fast cycle model of the RTL and defaults to a
3.072 MHz preview clock, exactly `48 kHz * 64`. Each WAV sample is an average
over the simulated chip clocks in that sample period, so the 1-bit mixer PWM is
low-pass filtered instead of point-sampled. The cocotb RTL test separately
checks that the Verilog mixer has the expected 64-clock average. Override
`SIM_CLOCK_HZ` for shorter experiments or slower experiments at the real
50 MHz chip clock.

`audio_sequence.json` supports compact ordered write blocks:

```json
{
  "writes": [
    { "GCTRL": 0 },
    { "CTRL0": 8, "PER0": 2, "MCTRL0": 8, "MPER0": 3, "VOL0": 8 },
    { "GCTRL": 1 },
    { "wait_ms": 2 },
    { "CTRL0": 0, "MCTRL0": 0, "wait_ms": 248 },
    { "CTRL0": 8, "PER0": 3, "MCTRL0": 8, "MPER0": 5, "wait_ms": 2 },
    { "CTRL0": 0, "MCTRL0": 16, "wait_ms": 248 }
  ]
}
```

Within each block, keys are processed in order. Register keys emit writes on
consecutive simulator clocks; `wait_ms` and `wait_cycles` advance the cursor.
Register keys may be `r00` through `r3F`, `0x00` through `0x3F`, or decimal
strings. The older absolute form still works:
`{ "time_ms": 250, "addr": 0, "data": 202 }`.

Named register keys are also accepted: `GCTRL`, `CTRL0..CTRL3`, `PER0..PER3`,
`MCTRL0..MCTRL3`, `MPER0..MPER3`, and `VOL0..VOL3`. `CTRLx`/`MCTRLx` bits
`[2:0]` select the prescaler tap, bit `3` resets the divider on the next
selected prescaler edge, and bit `4` enables hard sync from the paired divider.

To run gatelevel simulation, first harden your project and copy `../runs/wokwi/results/final/verilog/gl/{your_module_name}.v` to `gate_level_netlist.v`.

Then run:

```sh
make -B GATES=yes
```

If you wish to save the waveform in VCD format instead of FST format, edit tb.v to use `$dumpfile("tb.vcd");` and then run:

```sh
make -B FST=
```

This will generate `tb.vcd` instead of `tb.fst`.

## How to view the waveform file

Using GTKWave

```sh
gtkwave tb.fst tb.gtkw
```

Using Surfer

```sh
surfer tb.fst
```
