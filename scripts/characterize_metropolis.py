"""Metropolis acceptance characterization for the rtl_legalizer SA engine.

C1: compares the RTL LUT acceptance probability against true Metropolis
    exp(-delta/T) over a delta/T grid, quantifies the effective exponent,
    the delta >= T hard-rejection band, and the alias windows.
C2: measures placement-quality impact by running the (RTL-validated) golden
    SA with RTL acceptance vs exact Metropolis acceptance over several seeds.
"""

import math
import sys

sys.path.insert(0, "/home/ratik/Projects/RTLign")

from rtl_legalizer import audit, golden_model as gm, layout_gen

print("=== C1: RTL acceptance probability vs true Metropolis ===")
print(f"{'d/T':>8} {'p_true=exp(-x)':>15} {'p_rtl=thr/2^16':>15} {'ratio':>8}")
grid = [0.0625, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0, 16.0, 31.0, 32.0, 33.0, 64.0]
rows = []
for x in grid:
    t = 1000000
    delta = round(x * t)
    thr = gm.metropolis_threshold(delta, t)
    p_rtl = thr / 65536.0
    p_true = math.exp(-x)
    ratio = (p_rtl / p_true) if p_true > 1e-12 else float("inf")
    rows.append((x, p_true, p_rtl, ratio))
    print(f"{x:8.4f} {p_true:15.6f} {p_rtl:15.6f} {ratio:8.3f}")

# Effective exponent in the linear LUT region (x < 1, before saturation)
k_vals = [-math.log(p) / x for x, _, p, _ in rows if 0 < x < 1 and p > 0]
print(f"\neffective exponent k in exp(-k*x), x in (0,1): "
      f"{sum(k_vals)/len(k_vals):.3f} (true Metropolis: k=1)")

# Saturation: find the exact first rejected delta/T and the alias windows
t = 1000000
lo, hi = 0, 64 * t
delta_reject = None
for delta in range(1, 64 * t + 1, 997):  # coarse scan then refine
    pass
# exact: threshold is 0 iff ((4096*delta//T) >> 12) & 0x1F != 0
def p_rtl(delta, t):
    return gm.metropolis_threshold(delta, t) / 65536.0

# first x where p_rtl == 0
x = 0.0
first_zero = None
for i in range(1, 200000):
    delta = i * 1000  # delta/T = i/1000
    if p_rtl(delta, t) == 0.0:
        first_zero = i / 1000
        break
print(f"hard rejection starts at delta/T = {first_zero} (theory: 1.0)")

# alias windows in delta/T in [32, 96) where bits[16:12] == 0 -> accepts again
alias = []
step = t // 4096  # resolution ~0.000244 in x
d = 32 * t
while d < 96 * t:
    if p_rtl(d, t) > 0:
        alias.append((d / t, p_rtl(d, t)))
    d += step
if alias:
    xs = [a[0] for a in alias]
    print(f"alias windows (delta/T accepts again): {len(alias)} sampled points, "
          f"x range {min(xs):.3f}..{max(xs):.3f}, max p_rtl {max(a[1] for a in alias):.4f}")
else:
    print("no alias windows found in [32, 96)")

print("\n=== C2: placement quality, RTL acceptance vs exact Metropolis ===")
for label, src in [("mockup_168", "/home/ratik/Projects/RTLign/tests/data/golden/golden_input_168.hex")]:
    words = audit.read_hex_words(src)
    stats = {"rtl": [], "true": []}
    for seed in range(8):
        for variant in ("rtl", "true"):
            out, m = gm.sa_model(words, metropolis=variant,
                                 lfsr_seed=0xDEADBEEF + seed * 7919)
            hpwl = gm.cost_model(out)[1]
            stats[variant].append((m["final_cost"], hpwl, m["accepted_count"]))
    for variant in ("rtl", "true"):
        costs = [c for c, _, _ in stats[variant]]
        hpwls = [h for _, h, _ in stats[variant]]
        accs = [a for _, _, a in stats[variant]]
        print(f"{label} [{variant:4s}] cost mean {sum(costs)/len(costs):>9.0f} "
              f"min {min(costs):>9} | HPWL mean {sum(hpwls)/len(hpwls):>7.0f} "
              f"min {min(hpwls):>7} | acc mean {sum(accs)/len(accs):.0f}")

    rtl_mean = sum(c for c, _, _ in stats["rtl"]) / 8
    true_mean = sum(c for c, _, _ in stats["true"]) / 8
    print(f"{label}: exact Metropolis is {(rtl_mean - true_mean) / rtl_mean * 100:+.1f}% "
          f"vs RTL acceptance in mean final cost (negative = better)\n")

# same comparison on a dense small layout (SA does the heavy lifting there)
macros = layout_gen.gen_layout("dense", 24, seed=0)
words = [v & 0xFFFFFFFF for m in macros for v in m]
stats = {"rtl": [], "true": []}
for seed in range(8):
    for variant in ("rtl", "true"):
        out, m = gm.sa_model(words, metropolis=variant,
                             lfsr_seed=0xDEADBEEF + seed * 7919)
        stats[variant].append((m["final_cost"], gm.cost_model(out)[1]))
for variant in ("rtl", "true"):
    costs = [c for c, _ in stats[variant]]
    print(f"dense_24 [{variant:4s}] cost mean {sum(costs)/len(costs):>9.0f} min {min(costs):>9}")
rtl_mean = sum(c for c, _ in stats["rtl"]) / 8
true_mean = sum(c for c, _ in stats["true"]) / 8
print(f"dense_24: exact Metropolis is {(rtl_mean - true_mean) / rtl_mean * 100:+.1f}% "
      f"vs RTL acceptance in mean final cost")
