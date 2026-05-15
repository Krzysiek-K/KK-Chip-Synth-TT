/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module synth_divider (
    input  wire [7:0] reg_data,
    input  wire       write_prescaler_strobe,
    input  wire       write_timer_strobe,
    input  wire [7:0] prescaler_src,
    output wire       square_out,
    output wire       selected_prescaler_clk,
    output wire       divider_reset,
    output wire [2:0] prescaler_select
);

  reg [3:0] control_reg   = 4'h0;
  reg [7:0] timer_reg     = 8'h00;
  reg [7:0] timer_count   = 8'h00;
  reg       square_reg    = 1'b0;

  always @(posedge write_prescaler_strobe) begin
    control_reg <= reg_data[3:0];
  end

  always @(posedge write_timer_strobe) begin
    timer_reg <= reg_data;
  end

  assign prescaler_select       = control_reg[2:0];
  assign divider_reset          = control_reg[3];

  // This mux output clocks the timer counter and must remain visible to STA/CTS.
  (* keep = "true" *) wire prescaler_mux_clk;
  assign prescaler_mux_clk      = prescaler_src[prescaler_select];
  assign selected_prescaler_clk = prescaler_mux_clk;

  always @(posedge prescaler_mux_clk) begin
    if (divider_reset || (timer_count == timer_reg)) begin
      timer_count <= 8'h00;
      square_reg  <= divider_reset ? 1'b0 : ~square_reg;
    end else begin
      timer_count <= timer_count + 8'h01;
    end
  end

  assign square_out = square_reg;

endmodule
