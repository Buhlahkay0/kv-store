"""Draw throughput and latency charts from a results CSV.

Usage:
  python plot_results.py                      # reads results/results.csv
  python plot_results.py path/to/results.csv
"""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = Path(sys.argv[1] if len(sys.argv) > 1 else "results/results.csv")
out_dir = path.parent

rows = defaultdict(list)
for row in csv.DictReader(path.open()):
    rows[(int(row["nodes"]), row["phase"])].append(row)

node_counts = sorted({nodes for nodes, _ in rows})


def mean(nodes, phase, column):
    return statistics.mean(float(r[column]) for r in rows[(nodes, phase)])


def grouped_bars(ax, series, title, ylabel):
    """series is a list of (label, column, phase) and one group is drawn per node count."""
    width = 0.8 / len(series)
    tallest = 0
    for i, (label, column, phase) in enumerate(series):
        xs = [k + i * width for k in range(len(node_counts))]
        ys = [mean(n, phase, column) for n in node_counts]
        bars = ax.bar(xs, ys, width, label=label)
        labels = [f"{int(y + 0.5)}" if column == "ops_per_s" else f"{y:.1f}" for y in ys]
        ax.bar_label(bars, labels=labels, fontsize=8)
        tallest = max(tallest, *ys)
    ax.set_ylim(0, tallest * 1.3)   # leave room so the legend doesn't cover the bars
    ax.set_xticks([k + width * (len(series) - 1) / 2 for k in range(len(node_counts))])
    ax.set_xticklabels([str(n) for n in node_counts])
    ax.set_xlabel("Number of nodes")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper left", ncol=2)


fig, ax = plt.subplots(figsize=(6, 4))
grouped_bars(ax, [("SET", "ops_per_s", "set"), ("GET", "ops_per_s", "get")],
             "Throughput by number of nodes", "Operations per second")
fig.tight_layout()
fig.savefig(out_dir / "throughput.png", dpi=200)

fig, ax = plt.subplots(figsize=(6, 4))
grouped_bars(ax, [("SET average", "avg_ms", "set"), ("GET average", "avg_ms", "get"),
                  ("SET p99", "p99_ms", "set"), ("GET p99", "p99_ms", "get")],
             "Latency by number of nodes", "Milliseconds")
fig.tight_layout()
fig.savefig(out_dir / "latency.png", dpi=200)

print(f"Averages over {len(rows[(node_counts[0], 'set')])} run(s) per node count")
print("nodes  SET ops/s  GET ops/s  SET avg  GET avg  SET p99  GET p99")
for n in node_counts:
    print(f"{n:>5}  {int(mean(n, 'set', 'ops_per_s') + 0.5):>9}  {int(mean(n, 'get', 'ops_per_s') + 0.5):>9}  "
          f"{mean(n, 'set', 'avg_ms'):>7.1f}  {mean(n, 'get', 'avg_ms'):>7.1f}  "
          f"{mean(n, 'set', 'p99_ms'):>7.1f}  {mean(n, 'get', 'p99_ms'):>7.1f}")
print(f"Wrote {out_dir / 'throughput.png'} and {out_dir / 'latency.png'}")
