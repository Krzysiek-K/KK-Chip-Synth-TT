# SPDX-License-Identifier: Apache-2.0

import json
import os
import struct
import wave
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


DEFAULT_SEQUENCE = "audio_sequence.json"
DEFAULT_WAV = "chipsynth_render.wav"
DEFAULT_CLOCK_HZ = 48_000
DEFAULT_SAMPLE_RATE_HZ = 48_000


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


def _sample_from_bit_count(high_count, cycles_per_sample):
    if cycles_per_sample == 0:
        return 0

    duty = high_count / cycles_per_sample
    return max(-32768, min(32767, round((duty * 2.0 - 1.0) * 32767)))


def _write_cycle(write, clock_hz):
    if "cycle" in write:
        return int(write["cycle"])

    time_ms = float(write.get("time_ms", 0.0))
    return round((time_ms / 1000.0) * clock_hz)


@cocotb.test()
async def render_wav(dut):
    sequence = _load_sequence()
    clock_hz = int(os.environ.get("SIM_CLOCK_HZ", sequence.get("clock_hz", DEFAULT_CLOCK_HZ)))
    sample_rate_hz = int(
        os.environ.get("AUDIO_SAMPLE_RATE", sequence.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ))
    )
    duration_ms = float(sequence.get("duration_ms", 250.0))
    wav_path = Path(os.environ.get("AUDIO_WAV", sequence.get("output_wav", DEFAULT_WAV)))

    if clock_hz % sample_rate_hz != 0:
        raise ValueError("SIM_CLOCK_HZ must be an integer multiple of AUDIO_SAMPLE_RATE")

    cycles_per_sample = clock_hz // sample_rate_hz
    total_samples = round((duration_ms / 1000.0) * sample_rate_hz)
    total_cycles = total_samples * cycles_per_sample
    clock_period_ps = round(1_000_000_000_000 / clock_hz)
    if clock_period_ps % 2:
        clock_period_ps += 1

    writes = sorted(sequence.get("writes", []), key=lambda write: _write_cycle(write, clock_hz))
    next_write = 0
    high_count = 0
    sample_cycles = 0
    samples = []

    dut._log.info(
        "Rendering %s samples from %s at %s Hz using %s clock cycles/sample",
        total_samples,
        sequence["_path"],
        sample_rate_hz,
        cycles_per_sample,
    )

    cocotb.start_soon(Clock(dut.clk, clock_period_ps, unit="ps").start())

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0xC0
    dut.rst_n.value = 0

    for _ in range(8):
        await RisingEdge(dut.clk)

    dut.rst_n.value = 1

    for cycle in range(total_cycles):
        if next_write < len(writes) and _write_cycle(writes[next_write], clock_hz) <= cycle:
            write = writes[next_write]
            dut.ui_in.value = int(write["data"]) & 0xFF
            dut.uio_in.value = int(write["addr"]) & 0x3F
            next_write += 1
        else:
            dut.uio_in.value = 0xC0

        await RisingEdge(dut.clk)

        high_count += (int(dut.uo_out.value) >> 7) & 1
        sample_cycles += 1

        if sample_cycles == cycles_per_sample:
            samples.append(_sample_from_bit_count(high_count, cycles_per_sample))
            high_count = 0
            sample_cycles = 0

    _write_wav(wav_path, sample_rate_hz, samples)
    dut._log.info("Wrote %s", wav_path)
