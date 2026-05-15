# KK ChipSynth generated-clock constraints.
#
# The register write strobes are intentionally cheap decode clocks for small
# helper registers. Race-sensitive state, such as divider counters, must be
# covered by a real clock below so CTS and STA treat it as a clock tree.

source $::env(SCRIPTS_DIR)/base.sdc

proc chipsynth_unique {items} {
    set out {}
    foreach item $items {
        if { [lsearch -exact $out $item] < 0 } {
            lappend out $item
        }
    }
    return $out
}

proc chipsynth_without {items remove} {
    set out {}
    foreach item $items {
        if { [lsearch -exact $remove $item] < 0 } {
            lappend out $item
        }
    }
    return $out
}

proc chipsynth_nets {patterns} {
    set nets {}
    foreach pattern $patterns {
        foreach net [get_nets -quiet -hierarchical $pattern] {
            lappend nets $net
        }
    }
    return [chipsynth_unique $nets]
}

proc chipsynth_net_checked {name patterns} {
    set nets [chipsynth_nets $patterns]
    set count [llength $nets]
    puts "\[INFO] ChipSynth $name matched $count net(s)."
    if { $count != 1 } {
        puts "\[ERROR] ChipSynth $name patterns: $patterns"
        puts "\[ERROR] ChipSynth $name net matches: $nets"
        error "ChipSynth $name expected exactly one net, got $count."
    }
    return [lindex $nets 0]
}

proc chipsynth_clocked_clock_pins {} {
    set pins {}
    foreach clock [all_clocks] {
        foreach pin [all_registers -clock $clock -clock_pins] {
            lappend pins $pin
        }
    }
    return [chipsynth_unique $pins]
}

proc chipsynth_clock_pins_on_net {net} {
    set pins {}
    set register_clock_pins [all_registers -clock_pins]
    foreach pin [get_pins -quiet -of_objects $net] {
        if { [lsearch -exact $register_clock_pins $pin] >= 0 } {
            lappend pins $pin
        }
    }
    return [chipsynth_unique $pins]
}

proc chipsynth_generated_clock {name source master divide expected_sinks patterns} {
    set target [chipsynth_net_checked $name $patterns]

    create_generated_clock \
        -name $name \
        -source $source \
        -master_clock $master \
        -divide_by $divide \
        $target

    set clock [get_clocks -quiet $name]
    set clock_pins [all_registers -clock $clock -clock_pins]
    set clock_pin_count [llength $clock_pins]
    puts "\[INFO] ChipSynth generated clock $name reaches $clock_pin_count register clock pin(s)."
    if { $clock_pin_count != $expected_sinks } {
        puts "\[ERROR] ChipSynth generated clock $name clock pins: $clock_pins"
        error "ChipSynth generated clock $name expected $expected_sinks clock pin(s), got $clock_pin_count."
    }
}

proc chipsynth_helper_strobe {name expected_sinks patterns} {
    set target [chipsynth_net_checked $name $patterns]
    set clock_pins [chipsynth_clock_pins_on_net $target]
    set clock_pin_count [llength $clock_pins]
    puts "\[INFO] ChipSynth helper strobe $name reaches $clock_pin_count unbuffered register clock pin(s)."
    if { $clock_pin_count != $expected_sinks } {
        puts "\[ERROR] ChipSynth helper strobe $name clock pins: $clock_pins"
        error "ChipSynth helper strobe $name expected $expected_sinks clock pin(s), got $clock_pin_count."
    }
    return $clock_pins
}

set chipsynth_main_clk_pin [get_ports $clock_port]

# The selected prescaler clock is muxed by stable control register bits. The
# fastest selection is shared_clk_div[6], i.e. clk divided by 128. Slower
# selections are intentionally over-constrained by this clock.
#
# After synthesis, the timer flops are clocked by the kept top-level
# divider_clk net. The internal prescaler_mux_clk name may sit behind a
# preservation buffer, so it is not a reliable clock-pin root for STA coverage.
chipsynth_generated_clock chipsynth_divider_clk $chipsynth_main_clk_pin $clock_port 128 9 {
    divider_clk
}

# These write strobes intentionally remain small unbuffered helper-register
# clocks. They are not used for race-sensitive counters or state machines.
set chipsynth_allowed_unclocked_pins {}
foreach pin [chipsynth_helper_strobe chipsynth_write_prescaler 4 {
    *voice0.write_prescaler_strobe*
}] {
    lappend chipsynth_allowed_unclocked_pins $pin
}
foreach pin [chipsynth_helper_strobe chipsynth_write_timer 8 {
    *voice0.write_timer_strobe*
}] {
    lappend chipsynth_allowed_unclocked_pins $pin
}
foreach pin [chipsynth_helper_strobe chipsynth_write_global_control 1 {
    write_global_control
}] {
    lappend chipsynth_allowed_unclocked_pins $pin
}
set chipsynth_allowed_unclocked_pins [chipsynth_unique $chipsynth_allowed_unclocked_pins]

set chipsynth_clocked_pins [chipsynth_clocked_clock_pins]
set chipsynth_unclocked_pins [chipsynth_without [all_registers -clock_pins] $chipsynth_clocked_pins]
set chipsynth_unexpected_unclocked_pins [chipsynth_without $chipsynth_unclocked_pins $chipsynth_allowed_unclocked_pins]
puts "\[INFO] ChipSynth allowed helper-strobe clock pin count: [llength $chipsynth_allowed_unclocked_pins]"
puts "\[INFO] ChipSynth unexpected unclocked register clock pin count: [llength $chipsynth_unexpected_unclocked_pins]"
if { [llength $chipsynth_unexpected_unclocked_pins] != 0 } {
    puts "\[ERROR] ChipSynth unexpected unclocked register clock pins: $chipsynth_unexpected_unclocked_pins"
    error "ChipSynth generated-clock SDC did not cover every race-sensitive register clock pin."
}

puts "\[INFO] Setting clock uncertainty to: $::env(CLOCK_UNCERTAINTY_CONSTRAINT)"
set_clock_uncertainty $::env(CLOCK_UNCERTAINTY_CONSTRAINT) [all_clocks]

puts "\[INFO] Setting clock transition to: $::env(CLOCK_TRANSITION_CONSTRAINT)"
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) [all_clocks]

if { [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] && $::env(OPENLANE_SDC_IDEAL_CLOCKS) } {
    unset_propagated_clock [all_clocks]
} else {
    set_propagated_clock [all_clocks]
}

if { ![check_setup -multiple_clock -generated_clocks] } {
    error "ChipSynth generated-clock SDC sanity check failed."
}
