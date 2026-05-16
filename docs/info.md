<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

KK ChipSynth is a Tiny Tapeout custom chip synthesizer project inspired by
classic 8-bit home computer sound chips.

The first revision defines the top-level register bus and output pin contract:

- `ui_in[7:0]`: register data input
- `uio_in[5:0]`: register address
- `uio_in[6]`: active-low write strobe, `/WR`
- `uio_in[7]`: active-low chip select, `/CS`
- `uio_oe[7:0]`: always `8'h00`; every `uio` pin is treated as an input
- `uo_out[7]`: 1-bit audio output for an Audio PMOD
- `uo_out[6:0]`: debug/status output

The audio core exposes four channels. Each channel contains two divider
oscillators: a primary divider (`CTRLx`, `PERx`) and a modulation divider
(`MCTRLx`, `MPERx`). The two divider square outputs are NANDed to produce the
raw channel output. Each divider also exposes its period-compare signal to the
other divider as a hard-sync source.

Register addresses decode as three 2-bit one-hot groups:

- address bits `[5:4]`: channel select, channel `0..3`
- address bits `[3:2]`: function select
- address bits `[1:0]`: subregister select

The canonical register map is:

| Address pattern | Register | Description |
| --- | --- | --- |
| `0x00 + 0x10*x` | `CTRLx` | Primary divider control for channel `x` |
| `0x01 + 0x10*x` | `PERx` | Primary divider 8-bit period for channel `x` |
| `0x04 + 0x10*x` | `MCTRLx` | Modulation divider control for channel `x` |
| `0x05 + 0x10*x` | `MPERx` | Modulation divider 8-bit period for channel `x` |
| `0x08 + 0x10*x` | `VOLx` | Channel mixer volume mask for channel `x` |
| `0x3F` | `GCTRL` | Global control |

For `CTRLx` and `MCTRLx`, bits `[2:0]` select one of the eight shared
prescaler taps. Bit `3` forces that divider square output low and resets its
period counter on the next selected prescaler edge. Bit `4` enables hard sync:
when set, the paired divider's period-compare signal acts like the reset bit.
Bits `[7:5]` are ignored.

For `PERx` and `MPERx`, all eight bits are the period compare value. The
divider increments on the selected prescaler edge. When the counter equals the
period register, the counter returns to zero and the divider square output
toggles, unless reset or hard-sync reset is active.

For `VOLx`, bits `[3:0]` set the mixer volume from `0` to `15`. The mixer
compares a 4-bit phase derived from the shared fast counter with `VOLx`, so a
raw-high channel contributes `VOLx` high bits during each 16-slot channel
volume frame. `VOLx = 0` is silent and `VOLx = 15` is 15/16 duty.

For `GCTRL`, bit `0` is active-low `/reset`. Write `0` to hold the shared
prescaler reset and `1` to release it. `GCTRL` does not gate register writes or
the channel period counters.

The top level provides a shared clock divider. `synth_divider` receives an
8-bit tap window after an initial divide-by-64 stage, selects one tap using its
control register, then divides it with its period register. `synth_channel`
wraps two such dividers, cross-wires their hard-sync compare outputs, and NANDs
their square outputs.

The mixer receives the six fastest shared clock-divider bits as
`fast_counter[5:0]`. It uses `fast_counter[5:2]` as the 4-bit volume phase and
`fast_counter[1:0] ^ fast_counter[5:4]` as the channel mux select. Across any
complete 64-clock mixer frame, each channel is selected for 16 clocks and sees
all 16 volume phases exactly once. Therefore the average of `uo_out[7]` over
one mixer frame is `(ch0*VOL0 + ch1*VOL1 + ch2*VOL2 + ch3*VOL3) / 64`, where
`chx` is that channel's raw NANDed divider output. `uo_out[6:3]` exposes the
four volume-gated channel outputs directly for optional external mixing.

The shared divider uses ordinary `posedge clk` registers; reset is applied
through the D input so a clock edge while `/reset` is low clears the divider
without using resettable flops. The global reset bit does not gate register
writes or the channel period counters, which have their own reset bits. After
TT reset, software should write `0` to `GCTRL`, configure the channels, then
write `1` to `GCTRL` to release the prescaler from a known state.

Each selected prescaler tap is a generated clock for its divider period
counter. `src/generated_clocks.sdc` makes all eight divider mux outputs checked
generated clocks for LibreLane/OpenROAD, with exact sink-count checks so future
race-sensitive state must either use a covered clock tree or add a new
generated-clock constraint. The `/CS`, `/WR`, and address decode write strobes
intentionally remain cheap helper-register clocks and are explicitly
whitelisted by the SDC.

## How to test

Drive `/CS` and `/WR` low with a register address on `uio_in[5:0]` and data on
`ui_in[7:0]`.

The cocotb testbench can also render audio from a timed write sequence:

```sh
cd test
make render-wav
```

By default this reads `audio_sequence.json` and writes a 48 kHz mono
`chipsynth_render.wav` file.

## External hardware

Audio PMOD on `uo_out[7]`.
