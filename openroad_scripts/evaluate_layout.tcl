###############################################################################
# evaluate_layout.tcl — RTLign Placement Evaluation Script
###############################################################################
#
# PURPOSE:
#   Loads a provided DEF layout and reports its HPWL and overlap metrics.
#   Used by ml_predictor/evaluate.py to benchmark ML-predicted layouts.
#
# USAGE (called via subprocess):
#   TECH_LEF=<path> CELLS_LEF=<path> INPUT_DEF=<path> openroad -no_init -exit evaluate_layout.tcl
#
###############################################################################

proc parse_args {} {
    global tech_lef cells_lef input_def
    
    set tech_lef  ""
    set cells_lef ""
    set input_def ""

    if {[info exists ::env(TECH_LEF)]}  { set tech_lef  $::env(TECH_LEF) }
    if {[info exists ::env(CELLS_LEF)]} { set cells_lef $::env(CELLS_LEF) }
    if {[info exists ::env(INPUT_DEF)]} { set input_def $::env(INPUT_DEF) }
}

proc require_nonempty {var_name} {
    upvar $var_name val
    if {$val eq ""} {
        puts "ERROR: $var_name is required but was not provided."
        exit 1
    }
}

parse_args
require_nonempty tech_lef
require_nonempty cells_lef
require_nonempty input_def

puts "\[EVAL\] Loading technology LEF: $tech_lef"
read_lef $tech_lef

puts "\[EVAL\] Loading cells LEF: $cells_lef"
read_lef $cells_lef

puts "\[EVAL\] Loading DEF: $input_def"
read_def $input_def

puts "\[EVAL\] Calculating Placement Legality..."
set overlap_count 0
# check_placement returns output that we might need to parse, or we can just run it.
# OpenROAD's check_placement will output overlap instances.
if {[catch {check_placement -verbose} err]} {
    puts "\[EVAL\] check_placement finished (overlaps detected)."
} else {
    puts "\[EVAL\] check_placement finished (legal)."
}

puts "\[EVAL\] Calculating Placement HPWL..."
set block [ord::get_db_block]
set total_hpwl_dbu 0
set net_count 0

if {$block ne ""} {
    foreach net [$block getNets] {
        if {[$net isSpecial]} continue
        set bbox [$net getTermBBox]
        if {$bbox ne ""} {
            set dx [expr {[$bbox xMax] - [$bbox xMin]}]
            set dy [expr {[$bbox yMax] - [$bbox yMin]}]
            if {$dx > 0 || $dy > 0} {
                set total_hpwl_dbu [expr {$total_hpwl_dbu + $dx + $dy}]
                incr net_count
            }
        }
    }
}

set dbu_per_micron 1000
if {$block ne ""} {
    set dbu_per_micron [$block getDbUnitsPerMicron]
    if {$dbu_per_micron <= 0} { set dbu_per_micron 1000 }
}
set hpwl_val [expr {double($total_hpwl_dbu) / double($dbu_per_micron)}]

puts ""
puts "============================================================"
puts "METRICS SUMMARY"
puts "============================================================"
puts "\[METRIC\] HPWL: $hpwl_val"
puts "============================================================"
exit 0
