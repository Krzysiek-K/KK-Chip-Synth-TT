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

The starter audio core exposes one square-wave voice:

- register `0x00`: control register; bits `[2:0]` select the prescaler tap,
  bit `3` holds output low and resets the timer on the next selected prescaler edge
- register `0x01`: 8-bit timer divider
- register `0x3F`: global control; bit `0` is active-low `/reset`.
  Write `0` to hold the shared prescaler reset and `1` to release it.

The canonical register addresses above are the software-facing map. The address
decoder is intentionally minimal and may alias other addresses, including
aliases that update more than one register. The canonical addresses write only
their documented register.

The top level provides a shared clock divider. `synth_divider` receives an
8-bit tap window after an initial divide-by-64 stage, selects one tap using the
prescaler register, then divides it with the timer register to produce the
1-bit square-wave output. The shared divider uses ordinary `posedge clk`
registers; reset is applied through the D input so a clock edge while `/reset`
is low clears the divider without using resettable flops. The global reset bit
does not gate register writes or the voice timer, which has its own reset bit.
After TT reset, software should write `0` then configure the voice, then write
`1` to release the prescaler from a known state.

The selected prescaler tap is a generated clock for the divider timer counter.
`src/generated_clocks.sdc` makes that mux output a checked generated clock for
LibreLane/OpenROAD, with an exact sink-count check so future race-sensitive
state must either use a covered clock tree or add a new generated-clock
constraint. The `/CS`, `/WR`, and address decode write strobes intentionally
remain cheap helper-register clocks and are explicitly whitelisted by the SDC.

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
