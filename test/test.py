# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def bus_write(dut, addr, data):
    dut.ui_in.value = data
    dut.uio_in.value = addr & 0x3F  # /CS=0, /WR=0
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 0xC0 | (addr & 0x3F)  # /CS=1, /WR=1
    await ClockCycles(dut.clk, 1)


REG_GCTRL = 0x3F
REG_CTRL0 = 0x00
REG_PER0 = 0x01
REG_VOL0 = 0x02
REG_CTRL1 = 0x04
REG_PER1 = 0x05
REG_VOL1 = 0x06
REG_CTRL2 = 0x08
REG_PER2 = 0x09
REG_VOL2 = 0x0A
REG_CTRL3 = 0x0C
REG_PER3 = 0x0D
REG_VOL3 = 0x0E


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0xC0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Test ChipSynth pinout behavior")

    assert dut.uio_oe.value == 0x00
    assert dut.uio_out.value == 0x00

    await bus_write(dut, REG_GCTRL, 0x00)
    # Voice registers must remain writable while the global prescaler reset is held.
    await bus_write(dut, REG_CTRL0, 0x08)
    await bus_write(dut, REG_PER0, 0x02)
    await bus_write(dut, REG_VOL0, 0x08)
    await bus_write(dut, REG_CTRL1, 0x08)
    await bus_write(dut, REG_PER1, 0x03)
    await bus_write(dut, REG_VOL1, 0x08)
    await bus_write(dut, REG_CTRL2, 0x08)
    await bus_write(dut, REG_PER2, 0x04)
    await bus_write(dut, REG_VOL2, 0x08)
    await bus_write(dut, REG_CTRL3, 0x08)
    await bus_write(dut, REG_PER3, 0x05)
    await bus_write(dut, REG_VOL3, 0x08)
    assert int(dut.uo_out.value[2]) == 0

    await bus_write(dut, REG_GCTRL, 0x01)
    await ClockCycles(dut.clk, 256)

    assert int(dut.uo_out.value[2]) == 1

    await bus_write(dut, REG_CTRL0, 0x00)
    await bus_write(dut, REG_CTRL1, 0x00)
    await bus_write(dut, REG_CTRL2, 0x00)
    await bus_write(dut, REG_CTRL3, 0x00)

    audio_bits = []
    channel_bits = [[], [], [], []]
    selector_bits = []
    for _ in range(8192):
        await ClockCycles(dut.clk, 1)
        audio = dut.uo_out.value[7]
        if audio.is_resolvable:
            audio_bits.append(int(audio))
        for channel in range(4):
            bit = dut.uo_out.value[3 + channel]
            if bit.is_resolvable:
                channel_bits[channel].append(int(bit))
        selector = dut.uo_out.value[1:0]
        if selector.is_resolvable:
            selector_bits.append(int(selector))

    assert 0 in audio_bits
    assert 1 in audio_bits
    assert set(selector_bits) == {0, 1, 2, 3}
    for bits in channel_bits:
        assert 0 in bits
        assert 1 in bits
