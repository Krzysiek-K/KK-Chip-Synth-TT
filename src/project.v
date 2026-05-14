/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_KK_ChipSynth (
    input  wire [7:0] ui_in,    // Register data input
    output wire [7:0] uo_out,   // Audio output and debug/status
    input  wire [7:0] uio_in,   // Register address and active-low control inputs
    output wire [7:0] uio_out,  // Unused, because all uio pins are inputs
    output wire [7:0] uio_oe,   // Active high: 0=input, 1=output
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  wire [7:0] reg_data = ui_in;
  wire [5:0] reg_addr = uio_in[5:0];
  wire       wr_n     = uio_in[6];
  wire       cs_n     = uio_in[7];

  wire chip_selected = ~cs_n;
  wire write_active  = chip_selected & ~wr_n;

  // All uio pins are input-only for the ASIC interface.
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // Stub outputs for the first pinout step:
  // uo_out[7] is the 1-bit audio stream, held idle until the synth core exists.
  // uo_out[6:0] exposes simple bus status for bring-up/debug.
  assign uo_out[7]   = 1'b0;
  assign uo_out[6:0] = {chip_selected, write_active, reg_addr[4:0]};

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, clk, rst_n, reg_data, reg_addr[5], 1'b0};

endmodule
