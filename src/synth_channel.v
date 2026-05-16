/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module synth_channel (
    input  wire [7:0] bus_data,
    input  wire       write_channel,
    input  wire [3:0] write_function,
    input  wire [3:0] write_subreg,
    input  wire [7:0] prescaler_src,
    output wire       square_out
);

  wire write_CTRL  = write_channel & write_function[0] & write_subreg[0];
  wire write_PER   = write_channel & write_function[0] & write_subreg[1];
  wire write_MCTRL = write_channel & write_function[1] & write_subreg[0];
  wire write_MPER  = write_channel & write_function[1] & write_subreg[1];
  wire _unused = &{write_function[3:2], write_subreg[3:2], 1'b0};

  wire divider_out;
  wire divider_compare;
  wire mdivider_out;
  wire mdivider_compare;

  synth_divider divider (
      .bus_data(bus_data),
      .write_CTRL(write_CTRL),
      .write_PER(write_PER),
      .prescaler_src(prescaler_src),
      .hardsync_in(mdivider_compare),
      .square_out(divider_out),
      .compare_out(divider_compare)
  );

  synth_divider mdivider (
      .bus_data(bus_data),
      .write_CTRL(write_MCTRL),
      .write_PER(write_MPER),
      .prescaler_src(prescaler_src),
      .hardsync_in(divider_compare),
      .square_out(mdivider_out),
      .compare_out(mdivider_compare)
  );

  assign square_out = ~(divider_out & mdivider_out);

endmodule
