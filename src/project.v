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

  reg [15:0] phase_acc;
  reg [15:0] phase_inc;
  reg        gate;

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      phase_acc <= 16'h0000;
      phase_inc <= 16'h0000;
      gate      <= 1'b0;
    end else begin
      if (write_active) begin
        case (reg_addr)
          6'h00: phase_inc[7:0]  <= reg_data;
          6'h01: phase_inc[15:8] <= reg_data;
          6'h02: gate            <= reg_data[0];
          default: begin
          end
        endcase
      end

      if (gate) begin
        phase_acc <= phase_acc + phase_inc;
      end else begin
        phase_acc <= 16'h0000;
      end
    end
  end

  // All uio pins are input-only for the ASIC interface.
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // Starter voice: a register-controlled square wave.
  assign uo_out[7]   = gate & phase_acc[15];
  assign uo_out[6:0] = {chip_selected, write_active, gate, phase_acc[15:12]};

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, 1'b0};

endmodule
