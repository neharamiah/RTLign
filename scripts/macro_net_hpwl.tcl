# One-off ablation script: total HPWL vs macro-net-only HPWL.
# Same flow as evaluate_layout.tcl, plus per-net split by whether the net
# touches a BLOCK-class master (hard macro).
set tech_lef $::env(TECH_LEF)
set cells_lef $::env(CELLS_LEF)
set input_def $::env(INPUT_DEF)

read_lef $tech_lef
read_lef $cells_lef
read_def $input_def

if {[info exists ::env(HEAL_GP)] && $::env(HEAL_GP) == 1} {
    # Hold hard macros in place so healing re-places only standard cells.
    set block0 [ord::get_db_block]
    foreach inst [$block0 getInsts] {
        if {[[$inst getMaster] getType] == "BLOCK"} { $inst setPlacementStatus FIRM }
    }
    catch {global_placement -density 0.75}
    catch {detailed_placement}
    set block [ord::get_db_block]
}

set block [ord::get_db_block]
set total_dbu 0
set macro_dbu 0
set macro_net_count 0

foreach net [$block getNets] {
    if {[$net isSpecial]} continue
    set bbox [$net getTermBBox]
    if {$bbox eq ""} continue
    set dx [expr {[$bbox xMax] - [$bbox xMin]}]
    set dy [expr {[$bbox yMax] - [$bbox yMin]}]
    if {$dx <= 0 && $dy <= 0} continue
    set total_dbu [expr {$total_dbu + $dx + $dy}]
    set is_macro 0
    foreach term [$net getITerms] {
        set master [[$term getInst] getMaster]
        if {[$master getType] == "BLOCK"} { set is_macro 1 }
    }
    if {$is_macro} {
        set macro_dbu [expr {$macro_dbu + $dx + $dy}]
        incr macro_net_count
    }
}

set dbu [$block getDbUnitsPerMicron]
puts "\[METRIC\] HPWL: [expr {double($total_dbu) / double($dbu)}]"
puts "\[METRIC\] MACRO_NET_HPWL: [expr {double($macro_dbu) / double($dbu)}]"
puts "\[METRIC\] MACRO_NET_COUNT: $macro_net_count"
exit 0
