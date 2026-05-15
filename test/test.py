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

    await bus_write(dut, 0x00, 0x08)
    await bus_write(dut, 0x01, 0x02)
    await ClockCycles(dut.clk, 512)

    assert int(dut.uo_out.value[7]) == 0

    await bus_write(dut, 0x00, 0x00)

    audio_bits = []
    for _ in range(1024):
        await ClockCycles(dut.clk, 1)
        audio = dut.uo_out.value[7]
        if audio.is_resolvable:
            audio_bits.append(int(audio))

    assert 0 in audio_bits
    assert 1 in audio_bits
