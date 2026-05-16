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

  wire [7:0] bus_data = ui_in;
  wire [5:0] bus_addr = uio_in[5:0];
  wire       wr_n     = uio_in[6];
  wire       cs_n     = uio_in[7];

  wire chip_selected = ~cs_n;
  wire write_strobe  = chip_selected & ~wr_n;

  wire [3:0] write_channel = {
    bus_addr[5] & bus_addr[4],
    bus_addr[5] & ~bus_addr[4],
    ~bus_addr[5] & bus_addr[4],
    ~bus_addr[5] & ~bus_addr[4]
  };

  wire [3:0] write_function_decode = {
    bus_addr[3] & bus_addr[2],
    bus_addr[3] & ~bus_addr[2],
    ~bus_addr[3] & bus_addr[2],
    ~bus_addr[3] & ~bus_addr[2]
  };

  wire [3:0] write_function = write_function_decode & {4{write_strobe}};

  wire [3:0] write_subreg = {
    bus_addr[1] & bus_addr[0],
    bus_addr[1] & ~bus_addr[0],
    ~bus_addr[1] & bus_addr[0],
    ~bus_addr[1] & ~bus_addr[0]
  };

  wire write_GCTRL = write_channel[3] & write_function[3] & write_subreg[3];

  reg [13:0] shared_clk_div;
  reg        reg_GCTRL;

  always @(posedge write_GCTRL) begin
    reg_GCTRL <= bus_data[0];
  end

  wire shared_reset_n = rst_n & reg_GCTRL;
  wire [13:0] shared_clk_div_next = (shared_clk_div + 14'h0001) & {14{shared_reset_n}};
  wire [7:0] prescaler_src = shared_clk_div[13:6];

  always @(posedge clk) begin
    shared_clk_div <= shared_clk_div_next;
  end

  wire [3:0] square_out;
  wire [3:0] channel_out;
  wire [1:0] channel_select;
  wire       audio_out;

  // Generated clock roots for the divider timers; constrained in generated_clocks.sdc.
  (* keep = "true" *) wire channel_clk0;
  (* keep = "true" *) wire channel_mclk0;
  (* keep = "true" *) wire channel_clk1;
  (* keep = "true" *) wire channel_mclk1;
  (* keep = "true" *) wire channel_clk2;
  (* keep = "true" *) wire channel_mclk2;
  (* keep = "true" *) wire channel_clk3;
  (* keep = "true" *) wire channel_mclk3;

  synth_channel channel0 (
      .bus_data(bus_data),
      .write_channel(write_channel[0]),
      .write_function(write_function),
      .write_subreg(write_subreg),
      .prescaler_src(prescaler_src),
      .square_out(square_out[0]),
      .selected_prescaler_clk(channel_clk0),
      .selected_mprescaler_clk(channel_mclk0)
  );

  synth_channel channel1 (
      .bus_data(bus_data),
      .write_channel(write_channel[1]),
      .write_function(write_function),
      .write_subreg(write_subreg),
      .prescaler_src(prescaler_src),
      .square_out(square_out[1]),
      .selected_prescaler_clk(channel_clk1),
      .selected_mprescaler_clk(channel_mclk1)
  );

  synth_channel channel2 (
      .bus_data(bus_data),
      .write_channel(write_channel[2]),
      .write_function(write_function),
      .write_subreg(write_subreg),
      .prescaler_src(prescaler_src),
      .square_out(square_out[2]),
      .selected_prescaler_clk(channel_clk2),
      .selected_mprescaler_clk(channel_mclk2)
  );

  synth_channel channel3 (
      .bus_data(bus_data),
      .write_channel(write_channel[3]),
      .write_function(write_function),
      .write_subreg(write_subreg),
      .prescaler_src(prescaler_src),
      .square_out(square_out[3]),
      .selected_prescaler_clk(channel_clk3),
      .selected_mprescaler_clk(channel_mclk3)
  );

  synth_mixer mixer (
      .bus_data(bus_data),
      .write_channel(write_channel),
      .write_function(write_function),
      .write_subreg(write_subreg),
      .square_in(square_out),
      .fast_counter(shared_clk_div[5:0]),
      .channel_out(channel_out),
      .channel_select(channel_select),
      .audio_out(audio_out)
  );

  // All uio pins are input-only for the ASIC interface.
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  assign uo_out[7]   = audio_out;
  assign uo_out[6:3] = channel_out;
  assign uo_out[2:0] = {reg_GCTRL, channel_select};

  // List all unused inputs to prevent warnings.
  wire _unused = &{
    ena,
    channel_clk0,
    channel_mclk0,
    channel_clk1,
    channel_mclk1,
    channel_clk2,
    channel_mclk2,
    channel_clk3,
    channel_mclk3,
    1'b0
  };

endmodule
