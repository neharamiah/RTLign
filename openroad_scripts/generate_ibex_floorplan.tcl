read_lef data/generated_rtl_dataset/ibex/tech.lef
read_lef data/generated_rtl_dataset/ibex/cells.lef
read_verilog data/generated_rtl_dataset/ibex/ibex_synth_clean.v
link_design ibex_top
initialize_floorplan -utilization 60 -aspect_ratio 1.0 -core_space 10 -site unithd
make_tracks
place_pins -hor_layers {met3 met5} -ver_layers {met2 met4}
write_def data/generated_rtl_dataset/ibex/floorplan.def
