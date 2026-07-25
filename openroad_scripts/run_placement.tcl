###############################################################################
# run_placement.tcl — RTLign Dataset Generation Batch Script
###############################################################################
#
# PURPOSE:
#   Runs the OpenROAD placement flow for a single design instance and exports
#   the placed .def file. Called repeatedly by data_generator.py to generate
#   the training dataset (varying seeds and target densities).
#
# USAGE (non-interactive, called via subprocess from data_generator.py):
#   openroad -no_init -exit run_placement.tcl \
#     -design_name <name>  \
#     -tech_lef    <path>  \
#     -cells_lef   <path>  \
#     -input_def   <path>  \
#     -output_def  <path>  \
#     -target_density <float>
#
# USAGE (manual / testing):
#   Set the variables in the "CONFIGURATION" section below, then:
#   openroad -no_init -exit run_placement.tcl
#
# OUTPUT:
#   - <output_def>           : Placed DEF (PLACED components with coordinates)
#   - <output_dir>/place.log : Placement metrics (HPWL, overflow, density)
#
# DESIGN ASSUMPTIONS:
#   - Input DEF has a valid DIEAREA and ROW definitions (floorplan-complete)
#   - LEF files follow the ISPD 2015 / NanGate45 / FreePDK45 format
#   - Components section may have FIXED cells (endcaps, fill) — these are
#     preserved untouched
#
# PARAMETERS ACCEPTED:
#   design_name    - Design identifier string (used in log messages)
#   tech_lef       - Path to technology LEF (layers, vias, design rules)
#   cells_lef      - Path to cell library LEF (MACRO SIZE statements)
#   input_def      - Path to floorplan DEF (post-floorplan, pre-placement)
#   output_def     - Path where placed DEF will be written
#   target_density - Target cell density fraction (e.g. 0.70 for 70%)
#
###############################################################################

# ---------------------------------------------------------------------------
# 0. ARGUMENT PARSING
#    Supports being called with -<var> <val> flags OR with variables preset
# ---------------------------------------------------------------------------

# Parse arguments from environment variables (passed by data_generator.py)
proc parse_args {} {
    global design_name tech_lef cells_lef input_def output_def aspect_ratio core_utilization target_density

    # Defaults (safe fallback for interactive testing)
    set design_name    "gcd"
    set tech_lef       ""
    set cells_lef      ""
    set input_def      ""
    set output_def     ""
    set aspect_ratio   1.0
    set core_utilization 60.0
    set target_density 0.70

    if {[info exists ::env(DESIGN_NAME)]}    { set design_name    $::env(DESIGN_NAME) }
    if {[info exists ::env(TECH_LEF)]}       { set tech_lef       $::env(TECH_LEF) }
    if {[info exists ::env(CELLS_LEF)]}      { set cells_lef      $::env(CELLS_LEF) }
    if {[info exists ::env(INPUT_DEF)]}      { set input_def      $::env(INPUT_DEF) }
    if {[info exists ::env(OUTPUT_DEF)]}     { set output_def     $::env(OUTPUT_DEF) }
    if {[info exists ::env(ASPECT_RATIO)]}   { set aspect_ratio   $::env(ASPECT_RATIO) }
    if {[info exists ::env(CORE_UTILIZATION)]} { set core_utilization $::env(CORE_UTILIZATION) }
    if {[info exists ::env(TARGET_DENSITY)]} { set target_density $::env(TARGET_DENSITY) }
}

parse_args


# ---------------------------------------------------------------------------
# 1. VALIDATE REQUIRED INPUTS
# ---------------------------------------------------------------------------

proc require_nonempty {var_name} {
    upvar $var_name val
    if {$val eq ""} {
        puts "ERROR: -$var_name is required but was not provided."
        exit 1
    }
}

require_nonempty tech_lef
require_nonempty cells_lef
require_nonempty input_def
require_nonempty output_def


# ---------------------------------------------------------------------------
# 2. LOGGING SETUP
# ---------------------------------------------------------------------------

# Derive output directory from output_def path
set output_dir [file dirname $output_def]
file mkdir $output_dir

set log_file [file join $output_dir "place_${design_name}_ar${aspect_ratio}_u${core_utilization}_d${target_density}.log"]
set log_fh   [open $log_file w]

proc log {msg} {
    global log_fh
    set ts [clock format [clock seconds] -format "%H:%M:%S"]
    set line "\[$ts\] $msg"
    puts $line
    puts $log_fh $line
    flush $log_fh
}

log "============================================================"
log "RTLign Placement Run"
log "  design      : $design_name"
log "  tech_lef    : $tech_lef"
log "  cells_lef   : $cells_lef"
log "  input_def   : $input_def"
log "  output_def  : $output_def"
log "  aspect_ratio: $aspect_ratio"
log "  utilization : $core_utilization%"
log "  density     : $target_density"
log "============================================================"


# ---------------------------------------------------------------------------
# 3. READ LEF / DEF
# ---------------------------------------------------------------------------

log "Reading technology LEF: $tech_lef"
if {[catch {read_lef $tech_lef} err]} {
    log "ERROR reading tech LEF: $err"
    exit 1
}

log "Reading cell library LEF: $cells_lef"
if {[catch {read_lef $cells_lef} err]} {
    log "ERROR reading cells LEF: $err"
    exit 1
}

log "Reading input DEF: $input_def"
if {[catch {read_def $input_def} err]} {
    log "ERROR reading input DEF: $err"
    exit 1
}

log "Design loaded."

# ---------------------------------------------------------------------------
# 3.5 RE-INITIALIZE FLOORPLAN
#     Allows varying the die aspect ratio and core utilization
# ---------------------------------------------------------------------------

set site_name "unithd"
if {[info exists ::env(SITE_NAME)]} { set site_name $::env(SITE_NAME) }

log "Re-initializing floorplan (utilization=$core_utilization%, aspect_ratio=$aspect_ratio, site=$site_name)..."
if {[catch {
    initialize_floorplan -utilization $core_utilization -aspect_ratio $aspect_ratio -core_space 10 -site $site_name
} err]} {
    log "WARNING: initialize_floorplan failed with site=$site_name ($err). Retrying with site=core..."
    if {[catch {
        initialize_floorplan -utilization $core_utilization -aspect_ratio $aspect_ratio -core_space 10 -site core
    } err2]} {
        log "ERROR during initialize_floorplan: $err2"
        exit 1
    }
}
if {[catch { make_tracks } err]} {
    log "WARNING: make_tracks failed: $err"
}

log "Placing pins..."
if {[catch {
    place_pins -hor_layers {met3 met5} -ver_layers {met2 met4}
} err]} {
    log "WARNING: Pin placement with met3/met5 met2/met4 failed ($err). Retrying with met3 met4..."
    if {[catch {
        place_pins -hor_layers met3 -ver_layers met4
    } err2]} {
        log "ERROR during pin placement: $err2"
        exit 1
    }
}

if {[catch {
    set db [ord::get_db]
    set block [[$db getChip] getBlock]
    set bbox [$block getDieArea]
    log "  Die area    : [$bbox xMin] [$bbox yMin] -> [$bbox xMax] [$bbox yMax]"
    log "  Components  : [llength [$block getInsts]] instances"
} err]} {
    log "Warning: Could not read die stats: $err"
}


# ---------------------------------------------------------------------------
# 4. GLOBAL PLACEMENT
#    Uses OpenROAD's RePlAce engine via the place_design command.
#    Key parameters:
#      -density        : target utilisation (0.0–1.0)
#      -timing_driven  : disabled — we only care about wirelength, not slack
#      -routability_driven: disabled — pure placement, no routing awareness
# ---------------------------------------------------------------------------

log "Starting global placement (density=$target_density)..."

if {[catch {
    global_placement \
        -density         $target_density \
        -pad_left        0               \
        -pad_right       0
} err]} {
    log "ERROR during global placement: $err"
    exit 1
}

log "Global placement complete."


# ---------------------------------------------------------------------------
# 5. DETAILED PLACEMENT (LEGALIZATION)
#    Snaps cells to legal row positions. Preserves FIXED cells.
#    -max_displacement: allow large movement to handle dense designs
# ---------------------------------------------------------------------------

log "Starting detailed placement (legalization)..."

if {[catch {
    detailed_placement \
        -max_displacement [list 5000 5000]
} err]} {
    log "ERROR during detailed placement: $err"
    exit 1
}

log "Detailed placement complete."


# ---------------------------------------------------------------------------
# 6. CHECK PLACEMENT LEGALITY
# ---------------------------------------------------------------------------

log "Checking placement legality..."

if {[catch {check_placement -verbose} err]} {
    log "WARNING: Placement legality check failed: $err"
    # Do not exit — write the DEF anyway so the run is recorded
} else {
    log "Placement is legal."
}


# ---------------------------------------------------------------------------
# 7. REPORT METRICS
#    These are written to the log file and parsed by data_generator.py
#    to associate quality metrics with each generated DEF sample.
# ---------------------------------------------------------------------------

log "--- Placement Metrics ---"

if {[catch {
    set temp_wl_file [file join $output_dir "wl_temp_${design_name}_ar${aspect_ratio}_u${core_utilization}_d${target_density}.rpt"]
    report_wire_length -file $temp_wl_file -summary
    
    set fp [open $temp_wl_file r]
    set wl_data [read $fp]
    close $fp
    file delete $temp_wl_file

    foreach line [split $wl_data "\n"] {
        if {[string match "*Total wire length:*" $line]} {
            # Format: Total wire length: 123456 um
            set wl_val [lindex $line 3]
            log "METRIC hpwl $wl_val"
        }
    }
} err]} {
    log "METRIC hpwl N/A ($err)"
}

if {[catch {
    report_design_area
} err]} {
    log "Warning: Could not report design area: $err"
}

log "--- End Metrics ---"


# ---------------------------------------------------------------------------
# 8. WRITE OUTPUT DEF
# ---------------------------------------------------------------------------

log "Writing placed DEF to: $output_def"

if {[catch {write_def $output_def} err]} {
    log "ERROR writing output DEF: $err"
    exit 1
}

log "Output DEF written successfully."
log "============================================================"
log "Run complete: $design_name | AR=$aspect_ratio | Util=$core_utilization | density=$target_density"
log "============================================================"

close $log_fh
