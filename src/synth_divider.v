/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module synth_divider (
    input  wire [7:0] bus_data,
    input  wire       write_CTRL,
    input  wire       write_PER,
    input  wire [7:0] prescaler_src,
    output wire       square_out,
    output wire       selected_prescaler_clk,
    output wire       divider_reset,
    output wire [2:0] prescaler_select
);

  reg [3:0] reg_CTRL;
  reg [7:0] reg_PER;
  reg [7:0] per_count;
  reg       square_reg;

  always @(posedge write_CTRL) begin
    reg_CTRL <= bus_data[3:0];
  end

  always @(posedge write_PER) begin
    reg_PER <= bus_data;
  end

  assign prescaler_select       = reg_CTRL[2:0];
  assign divider_reset          = reg_CTRL[3];

  // This mux output clocks the timer counter and must remain visible to STA/CTS.
  (* keep = "true" *) wire prescaler_mux_clk;
  assign prescaler_mux_clk      = prescaler_src[prescaler_select];
  assign selected_prescaler_clk = prescaler_mux_clk;

  always @(posedge prescaler_mux_clk) begin
    if (divider_reset || (per_count == reg_PER)) begin
      per_count  <= 8'h00;
      square_reg  <= divider_reset ? 1'b0 : ~square_reg;
    end else begin
      per_count <= per_count + 8'h01;
    end
  end

  assign square_out = square_reg;

endmodule
