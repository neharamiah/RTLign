"""
Cycle-accurate Python golden model of the rtl_legalizer Verilog pipeline.

Replicates the exact RTL arithmetic (32-bit wraparound, unsigned/signed
comparison rules, fixed-point shifts, LUT Metropolis acceptance, LFSR
sampling schedule) so that RTL output can be cross-checked word for word.

Validation status is staged (see tests/test_golden_model.py):
  1. cost_model   vs sa_cost.v      (directed + real-scale vectors)
  2. greedy model vs legalizer_fsm.v (directed + random layouts)
  3. full SA      vs sa_engine.v    (metrics + final memory, small and full N)

Caveat: this file documents RTL behavior, including quirks (negative-
coordinate bbox collapse, exp(-4*d/T) effective Metropolis exponent).
"""

import math

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF

# exp LUT from sa_engine.v: 65535 * exp(-0.125 * i), 16-bit entries.
EXP_LUT = [65535, 57849, 51065, 45077, 39791, 35125, 31006, 27370,
           24161, 21327, 18826, 16618, 14669, 12949, 11430, 10090,
           8906, 7862, 6940, 6126, 5408, 4774, 4214, 3720,
           3283, 2898, 2558, 2258, 1993, 1759, 1553, 1371]


def s32(v):
    """Reinterpret a 32-bit pattern as a signed integer."""
    v &= MASK32
    return v - (1 << 32) if v & 0x80000000 else v


class LFSR32:
    """Galois LFSR, polynomial x^32+x^22+x^2+x+1, mask 0x80200003."""

    def __init__(self, seed):
        self.state = seed if seed != 0 else 0xDEADBEEF

    def advance(self):
        """One enable cycle. Returns the post-advance register value."""
        if self.state & 1:
            self.state = (self.state >> 1) ^ 0x80200003
        else:
            self.state >>= 1
        return self.state

    def peek(self):
        return self.state


# Default RTL parameters.
DEFAULTS = dict(
    num_lines=672, die_width=200260, die_height=201600,
    t_init=1000000, t_min=100, cool_shift=3, inner_iters=100, max_iters=1000,
    t0_samples=16, t0_scale_shift=2, t0_attempt_cap=64,
    w_wl=4, w_area=1, w_boundary=8, area_scale_shift=14,
    lfsr_seed=0xDEADBEEF,
)


def cost_model(mem, die_width=None, die_height=None, w_wl=None, w_area=None,
               w_boundary=None, area_scale_shift=None):
    """Exact model of one sa_cost evaluation over a flat word list.

    Returns (total_cost, hpwl, bbox_area, boundary) as unsigned integers.
    Replicates the unsigned min/max scans (negative coordinates are huge
    unsigned words) and the 32-bit hpwl wraparound.
    """
    p = DEFAULTS
    die_w = p["die_width"] if die_width is None else die_width
    die_h = p["die_height"] if die_height is None else die_height
    w_wl = p["w_wl"] if w_wl is None else w_wl
    w_area = p["w_area"] if w_area is None else w_area
    w_boundary = p["w_boundary"] if w_boundary is None else w_boundary
    shift = p["area_scale_shift"] if area_scale_shift is None else area_scale_shift

    num_macros = len(mem) // 4
    min_cx = min_cy = MASK32      # RTL resets mins to all-ones, maxes to zero
    max_cx = max_cy = 0
    min_left = min_bottom = MASK32
    max_right = max_top = 0
    accum_boundary = 0

    for i in range(num_macros):
        # Mask at entry: the RTL always sees 32-bit words, and callers may
        # pass raw signed Python ints (e.g. x=-100 from layout_gen).
        x = mem[i * 4] & MASK32
        y = mem[i * 4 + 1] & MASK32
        w = mem[i * 4 + 2] & MASK32
        h = mem[i * 4 + 3] & MASK32

        right = (x + w) & MASK32
        top = (y + h) & MASK32
        cx = (x + (w >> 1)) & MASK32
        cy = (y + (h >> 1)) & MASK32

        # Boundary penalties: signed view of x/y, signed view of right/top.
        sx, sy = s32(x), s32(y)
        s_right, s_top = s32(right), s32(top)
        pen_x = ((0 - sx) & MASK32) if sx < 0 else ((right - die_w) & MASK32 if s_right > die_w else 0)
        pen_y = ((0 - sy) & MASK32) if sy < 0 else ((top - die_h) & MASK32 if s_top > die_h else 0)
        accum_boundary = (accum_boundary + pen_x + pen_y) & MASK32

        min_cx = min(min_cx, cx)
        max_cx = max(max_cx, cx)
        min_cy = min(min_cy, cy)
        max_cy = max(max_cy, cy)
        min_left = min(min_left, x)
        max_right = max(max_right, right)
        min_bottom = min(min_bottom, y)
        max_top = max(max_top, top)

    span_cx = (max_cx - min_cx) & MASK32 if max_cx > min_cx else 0
    span_cy = (max_cy - min_cy) & MASK32 if max_cy > min_cy else 0
    hpwl = (span_cx + span_cy) & MASK32

    bbox_w = (max_right - min_left) if max_right > min_left else 0
    bbox_h = (max_top - min_bottom) if max_top > min_bottom else 0
    bbox_area = (bbox_w * bbox_h) & MASK64

    total = (w_wl * hpwl + w_area * (bbox_area >> shift)
             + w_boundary * accum_boundary) & MASK64
    return total, hpwl, bbox_area, accum_boundary


def _reflect(cand, size, die):
    """Exact model of the sa_engine boundary reflection chain (one axis).

    `cand` is the raw 32-bit candidate pattern, `size` the macro extent,
    `die` the die dimension. Returns the post-clamp 32-bit pattern.
    """
    c = cand & MASK32

    if s32(c) < 0:                       # soft reflection at negative edge
        c = (-s32(c)) & MASK32

    if (c + size) & MASK32 > die:        # unsigned overflow test (mixed signedness in RTL)
        c = ((die - size - ((c + size - die) & MASK32)) & MASK32) if die >= size else 0

    if s32(c) < 0:                       # hard clamp fallback
        c = 0

    if (c + size) & MASK32 > die:        # final guarantee (mirrors RTL even when unfixable)
        c = ((die - size) & MASK32) if die >= size else 0

    return c


def metropolis_threshold(delta, temperature):
    """Exact model of the RTL Metropolis threshold computation.

    ratio = ((delta << 12) / T) truncated to 32 bits. If bits [16:12] are
    nonzero the threshold saturates to 0 (always reject). Otherwise the
    threshold is EXP_LUT[ratio[11:7]] — effectively exp(-4*delta/T).
    """
    scaled = (delta << 12) & MASK64
    ratio = (scaled // temperature) & MASK32 if temperature > 0 else MASK32
    if (ratio >> 12) & 0x1F:
        return 0
    return EXP_LUT[(ratio >> 7) & 0x1F]


def sa_model(mem, num_iters_limit=None, track=None, metropolis="rtl",
             lfsr_seed=None, legal_moves=True):
    """Exact model of sa_engine (Pass 1) over a flat word list.

    Returns (out_mem, metrics_dict). metrics contains total_iters,
    accepted_count, final_cost, final_temp, and illegal_rejects. When `track`
    is a list, every iteration appends (sel_macro, dx, dy, accepted,
    current_cost, is_illegal) — is_illegal marks iterations rejected by the
    legality scan before Metropolis.

    metropolis="rtl" replicates the RTL LUT acceptance exactly.
    metropolis="true" replaces only the acceptance threshold with the exact
    Metropolis value 65535*exp(-delta/T) (same RNG stream, same moves), for
    quality comparisons in the verification report.

    legal_moves=True replicates the RTL legality scan: a candidate move that
    would overlap any other macro is rejected before cost evaluation (the
    engine scans collision_check over all macros first). The RNG stream is
    unaffected — the scan consumes no randomness. Set legal_moves=False for
    the pre-scan behavior (kept for the Metropolis characterization tools).

    LFSR schedule (validated against an RTL trace): the engine makes TWO
    LFSR advances per iteration — lfsr_en stays high through the APPLY_MOVE
    cycle because ST_PERTURB re-asserts it. Each iteration therefore
    consumes three words: sel_macro samples v_{2i}, the move bytes sample
    v_{2i+1}, and the Metropolis dice samples v_{2i+2}.
    """
    p = DEFAULTS
    num_macros = len(mem) // 4
    mem = [w & MASK32 for w in mem]  # normalize to the 32-bit RTL domain

    temperature = p["t_init"]
    inner_count = 0
    total_iters = 0
    accepted = 0
    illegal_rejects = 0
    rng = LFSR32(p["lfsr_seed"] if lfsr_seed is None else lfsr_seed)

    current_cost = cost_model(mem)[0]

    max_iters = p["max_iters"] if num_iters_limit is None else num_iters_limit

    # ------------------------------------------------------------------
    # Scale-aware T0 sampling (mirrors sa_engine ST_SET_TEMP): propose
    # candidate moves with the same LFSR schedule, accumulate |delta cost|
    # over legal candidates (always restored), then
    # T0 = clamp((accum >> log2(t0_samples)) << t0_scale_shift, t_min, 2^32-1).
    # Falls back to t_init when no legal candidate was sampled. Sampling
    # consumes no cooling: total_iters/inner_count/accepted are untouched.
    # ------------------------------------------------------------------
    accum = 0
    samples = 0
    attempts = 0
    while samples < p["t0_samples"] and attempts < p["t0_attempt_cap"]:
        attempts += 1
        sel = (rng.peek() & 0xFFFF) % num_macros
        rng.advance()
        mv = rng.peek()

        saved_x = mem[sel * 4]
        saved_y = mem[sel * 4 + 1]
        macro_w = mem[sel * 4 + 2]
        macro_h = mem[sel * 4 + 3]

        disp_scale = temperature >> 14
        if disp_scale == 0:
            disp_scale = 1
        raw_dx = s32((((mv >> 16) & 0xFF) - 128) * disp_scale) & MASK32
        raw_dy = s32((((mv >> 24) & 0xFF) - 128) * disp_scale) & MASK32
        cand_x = (saved_x + raw_dx) & MASK32
        cand_y = (saved_y + raw_dy) & MASK32
        new_x = _reflect(cand_x, macro_w, p["die_width"])
        new_y = _reflect(cand_y, macro_h, p["die_height"])

        rng.advance()  # dice word consumed, unused during sampling

        mem[sel * 4] = new_x
        mem[sel * 4 + 1] = new_y

        if legal_moves and any_overlap(mem, sel, num_macros):
            mem[sel * 4] = saved_x
            mem[sel * 4 + 1] = saved_y
            continue

        candidate_cost = cost_model(mem)[0]
        delta = abs(candidate_cost - current_cost)
        accum += delta
        samples += 1
        mem[sel * 4] = saved_x
        mem[sel * 4 + 1] = saved_y

    if samples == 0:
        temperature = p["t_init"]
    else:
        mean = accum >> (p["t0_samples"].bit_length() - 1)
        t0 = mean << p["t0_scale_shift"]
        temperature = min(max(t0, p["t_min"]), MASK32)

    while True:
        # ST_PERTURB: select macro from the pre-advance LFSR value.
        sel = (rng.peek() & 0xFFFF) % num_macros
        rng.advance()
        mv = rng.peek()  # first post-sel advance: move-byte sample

        saved_x = mem[sel * 4]
        saved_y = mem[sel * 4 + 1]
        macro_w = mem[sel * 4 + 2]
        macro_h = mem[sel * 4 + 3]

        # ST_APPLY_MOVE: temperature-scaled displacement + reflection.
        disp_scale = temperature >> 14
        if disp_scale == 0:
            disp_scale = 1
        raw_dx = s32((((mv >> 16) & 0xFF) - 128) * disp_scale) & MASK32
        raw_dy = s32((((mv >> 24) & 0xFF) - 128) * disp_scale) & MASK32
        cand_x = (saved_x + raw_dx) & MASK32
        cand_y = (saved_y + raw_dy) & MASK32
        new_x = _reflect(cand_x, macro_w, p["die_width"])
        new_y = _reflect(cand_y, macro_h, p["die_height"])

        rng.advance()  # second advance inside APPLY_MOVE cycle: dice sample
        dice = rng.peek() & 0xFFFF

        mem[sel * 4] = new_x
        mem[sel * 4 + 1] = new_y

        total_iters += 1
        prev_illegal = illegal_rejects

        # ST_LEGAL_SCAN: reject the candidate before cost evaluation when it
        # would overlap any other macro. No LFSR advances, so the dice word
        # sampled above is consumed but unused on this path (same as RTL).
        if legal_moves and any_overlap(mem, sel, num_macros):
            illegal_rejects += 1
            accepted_flag = False
            mem[sel * 4] = saved_x
            mem[sel * 4 + 1] = saved_y
        else:
            # ST_METROPOLIS
            candidate_cost = cost_model(mem)[0]
            if candidate_cost <= current_cost:
                accepted_flag = True
            else:
                delta = (candidate_cost - current_cost) & MASK64
                if metropolis == "rtl":
                    threshold = metropolis_threshold(delta, temperature)
                else:
                    threshold = int(65535 * math.exp(-delta / temperature)) if temperature > 0 else 0
                accepted_flag = dice < threshold
            if accepted_flag:
                current_cost = candidate_cost
                accepted += 1
            else:
                mem[sel * 4] = saved_x
                mem[sel * 4 + 1] = saved_y

        if track is not None:
            track.append((sel, new_x, new_y, accepted_flag, current_cost,
                          illegal_rejects > prev_illegal))

        # ST_CHECK_INNER: cooling and termination (pre-decay T compare).
        if inner_count + 1 >= p["inner_iters"]:
            inner_count = 0
            old_t = temperature
            temperature = (temperature - (temperature >> p["cool_shift"])) & MASK32
            if accepted == 0:
                # Frozen SA (mirrors sa_engine ST_CHECK_INNER): zero accepts
                # over a whole inner block; cooling can only reject more.
                break
            if old_t <= p["t_min"] or total_iters >= max_iters:
                break
        else:
            inner_count += 1
            if total_iters >= max_iters:
                break

    metrics = dict(total_iters=total_iters, accepted_count=accepted,
                   final_cost=current_cost, final_temp=temperature,
                   illegal_rejects=illegal_rejects)
    return mem, metrics


def any_overlap(mem, sel, num_macros):
    """True when macro `sel` overlaps any other macro in the flat word list."""
    x, y, w, h = mem[sel * 4], mem[sel * 4 + 1], mem[sel * 4 + 2], mem[sel * 4 + 3]
    for j in range(num_macros):
        if j == sel:
            continue
        if boxes_overlap(x, y, w, h,
                         mem[j * 4], mem[j * 4 + 1], mem[j * 4 + 2], mem[j * 4 + 3]):
            return True
    return False


def boxes_overlap(x1, y1, w1, h1, x2, y2, w2, h2):
    """Exact model of collision_check.v (strict unsigned AABB)."""
    right1, top1 = (x1 + w1) & MASK32, (y1 + h1) & MASK32
    right2, top2 = (x2 + w2) & MASK32, (y2 + h2) & MASK32
    return x1 < right2 and right1 > x2 and y1 < top2 and top1 > y2


def greedy_model(mem):
    """Exact model of legalizer_fsm.v (Pass 2) over a flat word list.

    Includes the min-overlap-axis push, pass-parity and macro-parity
    tie-breaks, die-edge wrap, the 8-sweep cap, and the MAX_RESOLVE_TRIES
    per-pair cap added by the verification effort. A single macro returns
    unchanged (the RTL's pair loop is skipped after the outer-bound fix).
    """
    p = DEFAULTS
    die_w, die_h = p["die_width"], p["die_height"]
    num_macros = len(mem) // 4
    mem = [w & MASK32 for w in mem]  # normalize to the 32-bit RTL domain

    if num_macros <= 1:
        return mem

    last_base = (num_macros - 1) * 4
    ptr_a, ptr_b = 0, 4
    resolved_any = False
    pass_count = 0

    while True:
        # FETCH
        x1, y1, w1, h1 = mem[ptr_a:ptr_a + 4]
        x2, y2, w2, h2 = mem[ptr_b:ptr_b + 4]

        # CHECK / RESOLVE loop (capped at MAX_RESOLVE_TRIES = 16)
        tries = 0
        while boxes_overlap(x1, y1, w1, h1, x2, y2, w2, h2) and tries < 16:
            tries += 1
            resolved_any = True

            right1, top1 = (x1 + w1) & MASK32, (y1 + h1) & MASK32
            overlap_x = (min(right1, (x2 + w2) & MASK32) - max(x1, x2)) & MASK32
            overlap_y = (min(top1, (y2 + h2) & MASK32) - max(y1, y2)) & MASK32

            even_pass = (pass_count & 1) == 0
            b2 = (ptr_b >> 2) & 1
            if even_pass:
                horizontal = overlap_x < overlap_y or (overlap_x == overlap_y and b2 == 0)
            else:
                horizontal = overlap_y < overlap_x or (overlap_x == overlap_y and b2 == 1)

            if horizontal:
                if x2 >= x1:  # unsigned
                    new_x2 = right1
                    if (right1 + w2) & MASK32 > die_w:
                        new_x2 = (x1 - w2) & MASK32 if x1 >= w2 else 0
                else:
                    new_x2 = (x1 - w2) & MASK32 if x1 >= w2 else 0
                x2 = new_x2
                mem[ptr_b] = x2
            else:
                if y2 >= y1:
                    new_y2 = top1
                    if (top1 + h2) & MASK32 > die_h:
                        new_y2 = (y1 - h2) & MASK32 if y1 >= h2 else 0
                else:
                    new_y2 = (y1 - h2) & MASK32 if y1 >= h2 else 0
                y2 = new_y2
                mem[ptr_b + 1] = y2

        # ADVANCE
        if ptr_b < last_base:
            ptr_b += 4
        elif (ptr_a + 4) < last_base:
            # RTL uses nonblocking assigns: ptr_b samples the OLD ptr_a.
            ptr_b = ptr_a + 8
            ptr_a = ptr_a + 4
        elif resolved_any and pass_count < 8:
            ptr_a, ptr_b = 0, 4
            resolved_any = False
            pass_count += 1
        else:
            return mem


def legalize_model(mem):
    """Full two-pass pipeline: SA then greedy. Returns (out_mem, sa_metrics)."""
    sa_mem, metrics = sa_model(mem)
    return greedy_model(sa_mem), metrics
