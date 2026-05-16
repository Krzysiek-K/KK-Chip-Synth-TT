`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Dump the signals to a FST file. You can view it with gtkwave or surfer.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;
  reg [5:0] audio_box_phase;
  reg [6:0] audio_box_accum;
  reg [6:0] audio_sum64;
`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  always @(posedge clk) begin
    if (!rst_n) begin
      audio_box_phase <= 6'h00;
      audio_box_accum <= 7'h00;
      audio_sum64     <= 7'h00;
    end else if (audio_box_phase == 6'd63) begin
      audio_sum64     <= audio_box_accum + (uo_out[7] === 1'b1);
      audio_box_accum <= 7'h00;
      audio_box_phase <= 6'h00;
    end else begin
      audio_box_accum <= audio_box_accum + (uo_out[7] === 1'b1);
      audio_box_phase <= audio_box_phase + 6'h01;
    end
  end

  tt_um_KK_ChipSynth user_project (

      // Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif

      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

endmodule
