"""Draw the report charts and table images from a results CSV.

Usage:
  python plot_results.py                      # reads results/results.csv
  python plot_results.py path/to/results.csv

The images are written to a figures/ folder next to the CSV file. They are 300 dpi
PNG files, 6.5 inches wide, which fits a page with 1 inch margins in LaTeX or Google Docs.
The key distribution images come from a separate experiment that places 30,000 keys on
a hash ring with 1, 10 and 160 virtual nodes per node, using the same uhashring library
as the router.
"""
import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from uhashring import HashRing

SET_COLOR, GET_COLOR = "#0072B2", "#E69F00"
NODE_COLORS = ["#0072B2", "#009E73", "#E69F00"]
RING_NODES = ["http://kv1:8080", "http://kv2:8080", "http://kv3:8080"]
RING_KEYS = 30000
VIRTUAL_NODE_COUNTS = [1, 10, 160]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#DDDDDD", "grid.linewidth": 0.7,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})

csv_path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/results.csv")
out_dir = csv_path.parent / "figures"
out_dir.mkdir(exist_ok=True)

rows = defaultdict(list)
for row in csv.DictReader(csv_path.open()):
    rows[(int(row["nodes"]), row["phase"])].append(row)
node_counts = sorted({nodes for nodes, _ in rows})


def mean(nodes, phase, column):
    return statistics.mean(float(r[column]) for r in rows[(nodes, phase)])


def half_up(x):
    return int(x + 0.5)


def save(fig, name):
    fig.savefig(out_dir / name, dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def grouped_bars(ax, series, fmt):
    """Draw one group of bars per node count. Each series is (label, color, phase, column)."""
    width = 0.8 / len(series)
    for i, (label, color, phase, column) in enumerate(series):
        xs = [k + i * width for k in range(len(node_counts))]
        ys = [mean(n, phase, column) for n in node_counts]
        bars = ax.bar(xs, ys, width * 0.92, label=label, color=color)
        ax.bar_label(bars, labels=[fmt(y) for y in ys], fontsize=8.5, padding=2)
    ax.set_xticks([k + width * (len(series) - 1) / 2 for k in range(len(node_counts))])
    ax.set_xticklabels([str(n) for n in node_counts])
    ax.set_xlabel("Number of nodes")


def draw_table(name, header, body, widths, bold_rows=()):
    fig, ax = plt.subplots(figsize=(6.5, 0.30 * (len(body) + 1.7)))
    ax.axis("off")
    table = ax.table(cellText=body, colLabels=header, colWidths=widths, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.55)
    for (r, _), cell in table.get_celld().items():
        cell.set_edgecolor("#BBBBBB")
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_facecolor("#E4ECF4")
            cell.set_text_props(weight="bold")
            cell.set_height(cell.get_height() * 1.6)
        elif r - 1 in bold_rows:
            cell.set_facecolor("#F3F6F9")
            cell.set_text_props(weight="bold")
        else:
            cell.set_facecolor("white")
    save(fig, name)


# Throughput chart
fig, ax = plt.subplots(figsize=(6.5, 3.4))
grouped_bars(ax, [("SET", SET_COLOR, "set", "ops_per_s"), ("GET", GET_COLOR, "get", "ops_per_s")],
             lambda y: f"{half_up(y):,}")
ax.set_ylabel("Operations per second")
ax.set_ylim(0, max(mean(n, p, "ops_per_s") for n in node_counts for p in ("set", "get")) * 1.18)
ax.legend(frameon=False, loc="upper left", ncol=2)
save(fig, "throughput.png")

# Latency chart, with average and p99 in separate panels so each has a readable scale
fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.4), sharey=True)
for ax, column, title in zip(axes, ("avg_ms", "p99_ms"), ("Average latency", "99th percentile latency")):
    grouped_bars(ax, [("SET", SET_COLOR, "set", column), ("GET", GET_COLOR, "get", column)],
                 lambda y: f"{y:.1f}")
    ax.set_title(title)
axes[0].set_ylabel("Milliseconds")
axes[0].set_ylim(0, max(mean(n, p, "p99_ms") for n in node_counts for p in ("set", "get")) * 1.18)
axes[0].legend(frameon=False, loc="upper right", ncol=2, fontsize=9)
fig.tight_layout()
save(fig, "latency.png")

# Averages table
draw_table(
    "table_averages.png",
    ["Nodes", "SET\nops/s", "GET\nops/s", "SET avg / p99\n(ms)", "GET avg / p99\n(ms)"],
    [[str(n), f"{half_up(mean(n, 'set', 'ops_per_s')):,}", f"{half_up(mean(n, 'get', 'ops_per_s')):,}",
      f"{mean(n, 'set', 'avg_ms'):.1f} / {mean(n, 'set', 'p99_ms'):.1f}",
      f"{mean(n, 'get', 'avg_ms'):.1f} / {mean(n, 'get', 'p99_ms'):.1f}"] for n in node_counts],
    [0.12, 0.16, 0.16, 0.28, 0.28])

# Table of every run, with a bold mean row after each node count
body, mean_rows = [], []
for n in node_counts:
    for run in sorted({int(r["run"]) for r in rows[(n, "set")]}):
        s = next(r for r in rows[(n, "set")] if int(r["run"]) == run)
        g = next(r for r in rows[(n, "get")] if int(r["run"]) == run)
        body.append([str(n), str(run), f"{int(float(s['ops_per_s'])):,}", f"{int(float(g['ops_per_s'])):,}",
                     f"{float(s['avg_ms']):.2f}", f"{float(g['avg_ms']):.2f}",
                     f"{float(s['p99_ms']):.2f}", f"{float(g['p99_ms']):.2f}"])
    mean_rows.append(len(body))
    body.append([str(n), "mean", f"{half_up(mean(n, 'set', 'ops_per_s')):,}",
                 f"{half_up(mean(n, 'get', 'ops_per_s')):,}",
                 f"{mean(n, 'set', 'avg_ms'):.1f}", f"{mean(n, 'get', 'avg_ms'):.1f}",
                 f"{mean(n, 'set', 'p99_ms'):.1f}", f"{mean(n, 'get', 'p99_ms'):.1f}"])
draw_table(
    "table_runs.png",
    ["Nodes", "Run", "SET\nops/s", "GET\nops/s", "SET avg\n(ms)", "GET avg\n(ms)", "SET p99\n(ms)", "GET p99\n(ms)"],
    body, [0.09, 0.11, 0.13, 0.13, 0.135, 0.135, 0.135, 0.135], bold_rows=mean_rows)

# Key distribution experiment, run on the real hash ring
distribution = {}
for virtual_nodes in VIRTUAL_NODE_COUNTS:
    ring = HashRing(nodes=RING_NODES, vnodes=virtual_nodes)
    counts = Counter(ring.get_node(f"key_{i}") for i in range(RING_KEYS))
    distribution[virtual_nodes] = [counts[node] for node in RING_NODES]

fig, ax = plt.subplots(figsize=(6.5, 3.4))
width = 0.26
for i, name in enumerate(("kv1", "kv2", "kv3")):
    xs = [k + (i - 1) * width for k in range(len(distribution))]
    ys = [100 * counts[i] / RING_KEYS for counts in distribution.values()]
    bars = ax.bar(xs, ys, width * 0.92, label=name, color=NODE_COLORS[i])
    ax.bar_label(bars, labels=[f"{y:.1f}%" for y in ys], fontsize=8.5, padding=2,
                 bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
ax.axhline(100 / 3, color="#555555", linestyle="--", linewidth=1, label="Even split (33.3%)")
ax.set_xticks(range(len(distribution)))
ax.set_xticklabels([str(k) for k in distribution])
ax.set_xlabel("Virtual nodes per node")
ax.set_ylabel(f"Share of {RING_KEYS:,} keys (%)")
ax.set_ylim(0, 82)
ax.legend(frameon=False, loc="upper right", ncol=2)
save(fig, "key_distribution.png")

draw_table(
    "table_key_distribution.png",
    ["Virtual\nnodes", "kv1", "kv2", "kv3"],
    [[str(k)] + [f"{c:,} ({100 * c / RING_KEYS:.1f}%)" for c in counts] for k, counts in distribution.items()],
    [0.19, 0.27, 0.27, 0.27])

print(f"Averages over {len(rows[(node_counts[0], 'set')])} run(s) per node count")
print("nodes  SET ops/s  GET ops/s  SET avg  GET avg  SET p99  GET p99")
for n in node_counts:
    print(f"{n:>5}  {half_up(mean(n, 'set', 'ops_per_s')):>9}  {half_up(mean(n, 'get', 'ops_per_s')):>9}  "
          f"{mean(n, 'set', 'avg_ms'):>7.1f}  {mean(n, 'get', 'avg_ms'):>7.1f}  "
          f"{mean(n, 'set', 'p99_ms'):>7.1f}  {mean(n, 'get', 'p99_ms'):>7.1f}")
print(f"Wrote {len(list(out_dir.glob('*.png')))} images to {out_dir}")
