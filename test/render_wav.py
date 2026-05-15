# SPDX-License-Identifier: Apache-2.0

import json
import os
import struct
import wave
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


DEFAULT_SEQUENCE = "audio_sequence.json"
DEFAULT_WAV = "chipsynth_render.wav"
DEFAULT_CLOCK_HZ = 196_608
DEFAULT_SAMPLE_RATE_HZ = 48_000

# Future friendly: add aliases such as "freq_lo": 0x00 here when the register
# map settles.
REGISTER_NAMES = {
    "global_control": 0x3F,
}


def _load_sequence():
    path = Path(os.environ.get("AUDIO_SEQUENCE", DEFAULT_SEQUENCE))
    with path.open("r", encoding="utf-8") as seq_file:
        sequence = json.load(seq_file)

    sequence["_path"] = str(path)
    return sequence


def _write_wav(path, sample_rate_hz, samples):
    frames = b"".join(struct.pack("<h", sample) for sample in samples)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(frames)


def _sample_from_bit(audio_bit):
    return 32767 if audio_bit else -32767


def _parse_int(value):
    if isinstance(value, str):
        return int(value, 0)

    return int(value)


def _cycles_from_ms(time_ms, clock_hz):
    return round((float(time_ms) / 1000.0) * clock_hz)


def _register_addr_from_key(key):
    if key in REGISTER_NAMES:
        addr = REGISTER_NAMES[key]
    elif key.startswith(("0x", "0X")) or key.isdigit():
        addr = _parse_int(key)
    elif len(key) == 3 and key[0] in ("r", "R"):
        addr = int(key[1:], 16)
    else:
        raise ValueError(f"Unknown register key {key!r}")

    if not 0 <= addr <= 0x3F:
        raise ValueError(f"Register address out of range: {key!r}")

    return addr


def _is_register_key(key):
    try:
        _register_addr_from_key(key)
    except ValueError:
        return False

    return True


def _absolute_write_cycle(write, clock_hz):
    if "cycle" in write:
        return _parse_int(write["cycle"])

    return _cycles_from_ms(write.get("time_ms", 0.0), clock_hz)


def _normalize_writes(sequence_writes, clock_hz):
    writes = []
    cursor_cycle = 0

    for step in sequence_writes:
        if not isinstance(step, dict):
            raise TypeError("Each write sequence step must be an object")

        if "addr" in step and "data" in step:
            write_cycle = _absolute_write_cycle(step, clock_hz)
            writes.append(
                {
                    "cycle": write_cycle,
                    "addr": _parse_int(step["addr"]),
                    "data": _parse_int(step["data"]),
                }
            )
            cursor_cycle = max(cursor_cycle, write_cycle + 1)
            continue

        for key, value in step.items():
            if key == "wait_cycles":
                cursor_cycle += _parse_int(value)
            elif key == "wait_ms":
                cursor_cycle += _cycles_from_ms(value, clock_hz)
            elif _is_register_key(key):
                writes.append(
                    {
                        "cycle": cursor_cycle,
                        "addr": _register_addr_from_key(key),
                        "data": _parse_int(value),
                    }
                )
                cursor_cycle += 1
            else:
                raise ValueError(f"Unsupported write sequence key {key!r} in {step!r}")

    return sorted(writes, key=lambda write: write["cycle"])


async def _drive_writes(dut, writes):
    current_cycle = 0

    for write in writes:
        write_cycle = int(write["cycle"])
        wait_cycles = write_cycle - current_cycle

        if wait_cycles > 0:
            await ClockCycles(dut.clk, wait_cycles)

        dut.ui_in.value = int(write["data"]) & 0xFF
        dut.uio_in.value = int(write["addr"]) & 0x3F
        await ClockCycles(dut.clk, 1)
        dut.uio_in.value = 0xC0 | (int(write["addr"]) & 0x3F)

        current_cycle = max(current_cycle + max(wait_cycles, 0), write_cycle) + 1


@cocotb.test()
async def render_wav(dut):
    sequence = _load_sequence()
    clock_hz = int(os.environ.get("SIM_CLOCK_HZ", sequence.get("clock_hz", DEFAULT_CLOCK_HZ)))
    sample_rate_hz = int(
        os.environ.get("AUDIO_SAMPLE_RATE", sequence.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ))
    )
    duration_ms = float(sequence.get("duration_ms", 250.0))
    wav_path = Path(os.environ.get("AUDIO_WAV", sequence.get("output_wav", DEFAULT_WAV)))

    total_samples = round((duration_ms / 1000.0) * sample_rate_hz)
    clock_period_ps = round(1_000_000_000_000 / clock_hz)
    if clock_period_ps % 2:
        clock_period_ps += 1

    writes = _normalize_writes(sequence.get("writes", []), clock_hz)
    samples = []

    dut._log.info(
        "Rendering %s samples from %s at %s Hz using %s Hz simulation clock",
        total_samples,
        sequence["_path"],
        sample_rate_hz,
        clock_hz,
    )

    cocotb.start_soon(Clock(dut.clk, clock_period_ps, unit="ps").start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0xC0
    dut.rst_n.value = 0

    for _ in range(8):
        await RisingEdge(dut.clk)

    dut.rst_n.value = 1
    cocotb.start_soon(_drive_writes(dut, writes))

    sample_period_ps = 1_000_000_000_000 / sample_rate_hz
    elapsed_ps = 0

    for sample_index in range(total_samples):
        next_elapsed_ps = round((sample_index + 1) * sample_period_ps)
        await Timer(next_elapsed_ps - elapsed_ps, unit="ps")
        elapsed_ps = next_elapsed_ps
        audio_bit = dut.uo_out.value[7]
        samples.append(_sample_from_bit(int(audio_bit) if audio_bit.is_resolvable else 0))

    _write_wav(wav_path, sample_rate_hz, samples)
    dut._log.info("Wrote %s", wav_path)
