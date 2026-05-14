# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


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
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Test ChipSynth pinout behavior")

    dut.ui_in.value = 0xA5
    dut.uio_in.value = 0x15  # /CS=0, /WR=0, reg_addr=0x15

    await ClockCycles(dut.clk, 1)

    assert dut.uio_oe.value == 0x00
    assert dut.uio_out.value == 0x00
    assert dut.uo_out.value == 0x75  # audio=0, selected=1, write=1, addr[4:0]=0x15

    dut.uio_in.value = 0xAA  # /CS=1, /WR=0, reg_addr=0x2a

    await ClockCycles(dut.clk, 1)

    assert dut.uo_out.value == 0x0A  # audio=0, selected=0, write=0, addr[4:0]=0x0a
