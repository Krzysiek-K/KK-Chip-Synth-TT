/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module synth_mixer (
    input  wire [7:0] bus_data,
    input  wire [3:0] write_channel,
    input  wire [3:0] write_function,
    input  wire [3:0] write_subreg,
    input  wire [3:0] square_in,
    input  wire [5:0] fast_counter,
    output wire [3:0] channel_out,
    output wire [1:0] channel_select,
    output wire       audio_out
);

  reg [3:0] reg_VOL0;
  reg [3:0] reg_VOL1;
  reg [3:0] reg_VOL2;
  reg [3:0] reg_VOL3;

  wire write_VOL0 = write_channel[0] & write_function[2] & write_subreg[0];
  wire write_VOL1 = write_channel[1] & write_function[2] & write_subreg[0];
  wire write_VOL2 = write_channel[2] & write_function[2] & write_subreg[0];
  wire write_VOL3 = write_channel[3] & write_function[2] & write_subreg[0];
  wire _unused = &{write_function[3], write_function[1:0], write_subreg[3:1], 1'b0};

  always @(posedge write_VOL0) begin
    reg_VOL0 <= bus_data[3:0];
  end

  always @(posedge write_VOL1) begin
    reg_VOL1 <= bus_data[3:0];
  end

  always @(posedge write_VOL2) begin
    reg_VOL2 <= bus_data[3:0];
  end

  always @(posedge write_VOL3) begin
    reg_VOL3 <= bus_data[3:0];
  end

  wire [3:0] volume_gate = {
    fast_counter[0],
    &fast_counter[1:0],
    &fast_counter[2:0],
    &fast_counter[3:0]
  };

  assign channel_out[0] = square_in[0] & |(volume_gate & reg_VOL0);
  assign channel_out[1] = square_in[1] & |(volume_gate & reg_VOL1);
  assign channel_out[2] = square_in[2] & |(volume_gate & reg_VOL2);
  assign channel_out[3] = square_in[3] & |(volume_gate & reg_VOL3);

  assign channel_select = fast_counter[1:0] ^ fast_counter[5:4];
  assign audio_out = channel_out[channel_select];

endmodule
