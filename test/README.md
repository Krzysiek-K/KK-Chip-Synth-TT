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

The renderer expects `SIM_CLOCK_HZ` to be an integer multiple of
`AUDIO_SAMPLE_RATE`. The default is `48000`, which is one simulator clock per
48 kHz output sample for quick register-sequence renders.

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
