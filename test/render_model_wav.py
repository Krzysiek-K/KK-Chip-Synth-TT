# SPDX-License-Identifier: Apache-2.0

import json
import os
import struct
import wave
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent

DEFAULT_SEQUENCE = TEST_DIR / "audio_sequence.json"
DEFAULT_WAV = TEST_DIR / "chipsynth_render.wav"
DEFAULT_SAMPLE_RATE_HZ = 48_000
DEFAULT_CLOCK_HZ = DEFAULT_SAMPLE_RATE_HZ * 64

REGISTER_NAMES = {
    "GCTRL": 0x3F,
    "GLOBAL_CONTROL": 0x3F,
    "CTRL0": 0x00,
    "PER0": 0x01,
    "MCTRL0": 0x04,
    "MPER0": 0x05,
    "VOL0": 0x08,
    "CTRL1": 0x10,
    "PER1": 0x11,
    "MCTRL1": 0x14,
    "MPER1": 0x15,
    "VOL1": 0x18,
    "CTRL2": 0x20,
    "PER2": 0x21,
    "MCTRL2": 0x24,
    "MPER2": 0x25,
    "VOL2": 0x28,
    "CTRL3": 0x30,
    "PER3": 0x31,
    "MCTRL3": 0x34,
    "MPER3": 0x35,
    "VOL3": 0x38,
}


class Divider:
    def __init__(self):
        self.reg_CTRL = 0
        self.reg_PER = 0
        self.per_count = 0
        self.square = 0
        self.prev_clk = 0

    def compare(self):
        return self.per_count == self.reg_PER

    def write_CTRL(self, data):
        self.reg_CTRL = data & 0x1F

    def write_PER(self, data):
        self.reg_PER = data & 0xFF

    def tick(self, prescaler_src, hardsync_in):
        selected_clk = (prescaler_src >> (self.reg_CTRL & 0x07)) & 1
        rising_edge = selected_clk and not self.prev_clk
        self.prev_clk = selected_clk

        if not rising_edge:
            return

        divider_reset = ((self.reg_CTRL >> 3) & 1) or (((self.reg_CTRL >> 4) & 1) and hardsync_in)
        if divider_reset or self.compare():
            self.per_count = 0
            self.square = 0 if divider_reset else (self.square ^ 1)
        else:
            self.per_count = (self.per_count + 1) & 0xFF


class Channel:
    def __init__(self):
        self.divider = Divider()
        self.mdivider = Divider()

    def write(self, function, subreg, data):
        if function == 0 and subreg == 0:
            self.divider.write_CTRL(data)
        elif function == 0 and subreg == 1:
            self.divider.write_PER(data)
        elif function == 1 and subreg == 0:
            self.mdivider.write_CTRL(data)
        elif function == 1 and subreg == 1:
            self.mdivider.write_PER(data)

    def tick(self, prescaler_src):
        divider_compare = self.divider.compare()
        mdivider_compare = self.mdivider.compare()
        self.divider.tick(prescaler_src, mdivider_compare)
        self.mdivider.tick(prescaler_src, divider_compare)

    def raw_out(self):
        return 0 if (self.divider.square and self.mdivider.square) else 1


def _write_wav(path, sample_rate_hz, samples):
    frames = b"".join(struct.pack("<h", sample) for sample in samples)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(frames)


def _sample_from_level(level, max_level):
    scaled = (2.0 * (float(level) / float(max_level))) - 1.0
    return round(max(-1.0, min(1.0, scaled)) * 32767)


def _parse_int(value):
    if isinstance(value, str):
        return int(value, 0)

    return int(value)


def _cycles_from_ms(time_ms, clock_hz):
    return round((float(time_ms) / 1000.0) * clock_hz)


def _register_addr_from_key(key):
    name = key.upper()
    if name in REGISTER_NAMES:
        addr = REGISTER_NAMES[name]
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


def _apply_write(channels, reg_VOL, state, addr, data):
    channel = (addr >> 4) & 0x03
    function = (addr >> 2) & 0x03
    subreg = addr & 0x03

    if channel == 3 and function == 3 and subreg == 3:
        state["reg_GCTRL"] = data & 0x01
    elif function == 2 and subreg == 0:
        reg_VOL[channel] = data & 0x0F
    else:
        channels[channel].write(function, subreg, data)


def _render(sequence):
    clock_hz = int(os.environ.get("SIM_CLOCK_HZ", sequence.get("clock_hz", DEFAULT_CLOCK_HZ)))
    sample_rate_hz = int(
        os.environ.get("AUDIO_SAMPLE_RATE", sequence.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ))
    )
    duration_ms = float(sequence.get("duration_ms", 250.0))
    total_samples = round((duration_ms / 1000.0) * sample_rate_hz)
    total_cycles = round((duration_ms / 1000.0) * clock_hz)

    channels = [Channel() for _ in range(4)]
    reg_VOL = [0, 0, 0, 0]
    state = {"reg_GCTRL": 0, "shared_clk_div": 0}
    writes = _normalize_writes(sequence.get("writes", []), clock_hz)
    write_index = 0
    samples = []
    audio_accum = 0
    audio_count = 0
    next_sample_index = 0
    next_sample_cycle = round((next_sample_index + 1) * clock_hz / sample_rate_hz)

    for cycle in range(total_cycles):
        while write_index < len(writes) and writes[write_index]["cycle"] == cycle:
            write = writes[write_index]
            _apply_write(channels, reg_VOL, state, write["addr"] & 0x3F, write["data"] & 0xFF)
            write_index += 1

        fast_counter = state["shared_clk_div"] & 0x3F
        volume_phase = (fast_counter >> 2) & 0x0F
        channel_select = (fast_counter & 0x03) ^ ((fast_counter >> 4) & 0x03)
        channel_out = [
            channels[index].raw_out() & (1 if volume_phase < reg_VOL[index] else 0)
            for index in range(4)
        ]
        audio_accum += channel_out[channel_select]
        audio_count += 1

        if state["reg_GCTRL"]:
            state["shared_clk_div"] = (state["shared_clk_div"] + 1) & 0x3FFF
        else:
            state["shared_clk_div"] = 0

        prescaler_src = (state["shared_clk_div"] >> 6) & 0xFF
        for channel in channels:
            channel.tick(prescaler_src)

        if cycle + 1 >= next_sample_cycle:
            samples.append(_sample_from_level(audio_accum, max(audio_count, 1)))
            audio_accum = 0
            audio_count = 0
            next_sample_index += 1
            next_sample_cycle = round((next_sample_index + 1) * clock_hz / sample_rate_hz)

    while len(samples) < total_samples:
        samples.append(_sample_from_level(audio_accum, max(audio_count, 1)))

    return sample_rate_hz, samples[:total_samples]


def main():
    sequence_path = Path(os.environ.get("AUDIO_SEQUENCE", DEFAULT_SEQUENCE))
    with sequence_path.open("r", encoding="utf-8") as seq_file:
        sequence = json.load(seq_file)

    wav_path = Path(os.environ.get("AUDIO_WAV", sequence.get("output_wav", DEFAULT_WAV)))
    if not wav_path.is_absolute():
        wav_path = TEST_DIR / wav_path

    sample_rate_hz, samples = _render(sequence)
    _write_wav(wav_path, sample_rate_hz, samples)
    print(f'Wrote "{wav_path}"')


if __name__ == "__main__":
    main()
