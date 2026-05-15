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
  wire write_strobe  = chip_selected & ~wr_n;

  wire write_prescaler = write_strobe & (reg_addr == 6'h00);
  wire write_timer     = write_strobe & (reg_addr == 6'h01);

  reg [13:0] shared_clk_div = 14'h0000;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      shared_clk_div <= 14'h0000;
    end else begin
      shared_clk_div <= shared_clk_div + 14'h0001;
    end
  end

  wire       divider_out;
  // Generated clock root for the divider timer; constrained in generated_clocks.sdc.
  (* keep = "true" *) wire divider_clk;
  wire       divider_reset;
  wire [2:0] divider_prescaler;

  synth_divider voice0 (
      .reg_data(reg_data),
      .write_prescaler_strobe(write_prescaler),
      .write_timer_strobe(write_timer),
      .prescaler_src(shared_clk_div[13:6]),
      .square_out(divider_out),
      .selected_prescaler_clk(divider_clk),
      .divider_reset(divider_reset),
      .prescaler_select(divider_prescaler)
  );

  // All uio pins are input-only for the ASIC interface.
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // Starter voice: a two-register divider oscillator.
  assign uo_out[7]   = divider_out;
  assign uo_out[6:0] = {chip_selected, write_strobe, divider_reset, divider_out, divider_prescaler};

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, 1'b0};

endmodule
