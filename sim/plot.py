"""Read a `sim --record` directory: PWM duty per phase from the TIM1 pad edges (gpio.jsonl) and the polled terminal
values (uart.jsonl). Writes a PNG and prints the measured numbers."""
import json, re, sys, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rec, out, log = sys.argv[1], sys.argv[2], sys.argv[3]
PADS = {("gpioPortA", 8): "U", ("gpioPortA", 9): "V", ("gpioPortA", 10): "W", ("gpioPortB", 13): "Un"}
ev = {k: [] for k in PADS.values()}
for l in open(f"{rec}/gpio.jsonl"):
    d = json.loads(l)
    k = PADS.get((d["port"], d["pin"]))
    if k:
        ev[k].append((d["t"], d["level"]))

def cycles(e):
    """(rise time, period, duty) for every complete high-pulse cycle of one pad."""
    rises = [t for t, v in e if v]
    out = []
    for r0, r1 in zip(rises, rises[1:]):
        fall = next((t for t, v in e if not v and r0 < t < r1), None)
        if fall is not None:
            out.append((r0, r1 - r0, (fall - r0) / (r1 - r0)))
    return out

cy = {p: [c for c in cycles(ev[p]) if c[2] > 0.4] for p in "UVW"}   # drops the ramp-in cycle
t0 = ev["U"][0][0]
period = st.median(c[1] for c in cy["U"])
# dead time: PA8 falls -> PB13 (complementary) rises, same cycle
fallU = [t for t, v in ev["U"] if not v]
riseUn = [t for t, v in ev["Un"] if v]
dead = [min(r for r in riseUn if r > f) - f for f in fallU[200:400]]
dead_ns = st.median(dead) * 1e9

# polled terminal values: echo line "get a,b,c" then one value per line
names = None
rows = []
for l in open(f"{rec}/uart.jsonl"):
    d = json.loads(l)
    if d["label"].endswith("← term") or "term" not in d["label"]:
        continue
    m = re.match(r"get ([\w,]+)", d["text"])
    if m:
        names = m.group(1).split(","); cur = [d["t"]]; rows.append(cur); continue
    if names and re.fullmatch(r"-?\d+(\.\d+)?", d["text"].strip()) and len(cur) <= len(names):
        cur.append(float(d["text"]))
rows = [r for r in rows if len(r) == len(names) + 1]
col = {n: [r[i + 1] for r in rows] for i, n in enumerate(names)}
tt = [r[0] for r in rows]

# CAN frames the inverter sent after the terminal mapped fstat (0x180) and amp (0x181): int16 little endian, gain 1
can = {0x180: [], 0x181: []}
for l in open(log):
    m = re.search(r"CAN RX id=0x(\w+) data=(\w+)", l)
    if m and int(m.group(1), 16) in can:
        can[int(m.group(1), 16)].append(int.from_bytes(bytes.fromhex(m.group(2)), "little", signed=True))
fig, ax = plt.subplots(4, 1, figsize=(10, 12), constrained_layout=True)
for p, c in zip("UVW", ("#1f77b4", "#d62728", "#2ca02c")):
    ax[0].plot([x[0] for x in cy[p]], [100 * x[2] for x in cy[p]], lw=0.8, color=c, label=f"phase {p}")
ax[0].set(ylabel="PWM duty (%)", title="stm32-sine on a simulated STM32F103RC: TIM1 duty per cycle, from the PA8/PA9/PA10 pad edges")
ax[0].legend(loc="upper right", ncol=3)
zt = t0 + 1.0
for p_, c in zip("UVW", ("#1f77b4", "#d62728", "#2ca02c")):
    z = [x for x in cy[p_] if zt <= x[0] <= zt + 0.4]
    ax[1].plot([x[0] - zt for x in z], [100 * x[2] for x in z], lw=1, color=c, label=f"phase {p_}")
ax[1].set(ylabel="PWM duty (%)", xlabel="s", title="0.4 s zoom: three phases 120 degrees apart, 5 Hz")
ax[1].legend(loc="upper right", ncol=3)
z0 = t0 + 1.0
for p, c, off in (("U", "#1f77b4", 2), ("Un", "#9467bd", 0)):
    e = [(t, v) for t, v in ev[p] if z0 <= t <= z0 + 3 * period]
    xs, ys = [], []
    for t, v in e:
        xs += [(t - z0) * 1e6] * 2; ys += [1 - v + off, v + off]
    ax[2].step([(t - z0) * 1e6 for t, v in e], [v + off * 1.5 for t, v in e], where="post", color=c, label={"U": "PA8 (TIM1_CH1)", "Un": "PB13 (TIM1_CH1N)"}[p])
ax[2].set(xlabel="us", yticks=[], title=f"three PWM periods: {period*1e6:.1f} us, dead time {dead_ns:.0f} ns between PA8 low and PB13 high")
ax[2].legend(loc="upper right")
ax[3].plot(tt, col["fstat"], "o-", ms=3, label="fstat (Hz)")
ax[3].plot(tt, [x / 100 for x in col["amp"]], "s-", ms=3, label="amp / 100 (dig)")
ax[3].plot(tt, col["cpuload"], "^-", ms=3, label="cpuload (%)")
ax[3].plot(tt, [x * 5 for x in col["opmode"]], "x-", ms=3, label="opmode x5 (1 = RUN)")
ax[3].set(xlabel="virtual time (s)", title="serial terminal (USART3, `get`, every 100 ms)")
ax[3].legend(loc="center right")
fig.savefig(out, dpi=110)

d = {p: [x[2] * 100 for x in cy[p]] for p in "UVW"}
print(f"PWM start {t0:.4f} s; period {period*1e6:.2f} us = {1/period/1e3:.2f} kHz; cycles U/V/W {len(cy['U'])}/{len(cy['V'])}/{len(cy['W'])}")
print(f"dead time PA8 fall -> PB13 rise: {dead_ns:.0f} ns")
for p in "UVW":
    print(f"duty {p}: min {min(d[p]):.2f} %  max {max(d[p]):.2f} %  mean {st.mean(d[p]):.2f} %")
print(f"terminal: {len(rows)} polls; fstat last {col['fstat'][-1]} Hz, amp last {col['amp'][-1]}, cpuload last {col['cpuload'][-1]} %")
print(f"CAN: {len(can[0x180])} frames 0x180 (fstat), {len(can[0x181])} frames 0x181 (amp); last fstat {can[0x180][-1]} Hz, last amp {can[0x181][-1]}")
