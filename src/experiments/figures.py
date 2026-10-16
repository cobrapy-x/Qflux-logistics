"""Draw the figures in figures/ from the numbers in results/summary.json."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")                     # no window needed
import matplotlib.pyplot as plt  # noqa: E402

from . import config as C  # noqa: E402

# A colour-blind-checked categorical palette (blue, orange, aqua, yellow) + neutral grey.
BLUE, ORANGE, AQUA, YELLOW, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a8880"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e2dc"

plt.rcParams.update({
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 150, "savefig.bbox": "tight",
})


def _sources(main: dict) -> list[tuple[str, str, dict]]:
    """(label, colour, numbers) for every source we have results for."""
    rows = [("Random\nguess", GREY, {"p_valid": main["random"]["p_valid"], "p_best": main["random"]["p_best"]}),
            ("Ideal\nsimulator", BLUE, main["ideal_sampled"]),
            (f"Noisy\nsimulator\n{main['noisy']['backend']}", ORANGE,
             {**main["noisy"], "p_valid_se": main["noisy"]["p_valid_sd"], "p_best_se": main["noisy"]["p_best_sd"]})]
    hw = main.get("hardware")
    if hw:
        rows.append((f"IBM\nhardware\n{hw['backend']}", AQUA, hw))
    return rows


def main_result_figure(summary: dict, path) -> None:
    main = summary["main"]
    rows = _sources(main)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.1, 1.1, 1.25]})

    for ax, key, title in ((ax1, "p_valid", "Shots that obey the van-capacity rule"),
                           (ax2, "p_best", "Shots that are the optimal plan")):
        for i, (label, colour, r) in enumerate(rows):
            err = r.get(key + "_se")
            ax.bar(i, r[key] * 100, color=colour, width=0.65, yerr=(err * 100 if err else None),
                   capsize=4, error_kw={"ecolor": INK2, "elinewidth": 1})
            ax.annotate(f"{r[key] * 100:.1f}%" if r[key] >= 0.01 else f"{r[key] * 100:.2f}%",
                        (i, r[key] * 100 + (err * 100 if err else 0)), ha="center", va="bottom",
                        fontsize=9, color=INK, xytext=(0, 3), textcoords="offset points")
        # three short lines per label, so long backend names never run into each other
        ax.set_xticks(range(len(rows)), [r[0] for r in rows], fontsize=7.5, linespacing=1.15)
        ax.set_ylabel("% of shots")
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, max(r[2][key] for r in rows) * 100 * 1.3)

    # the optimal plan on the map
    pts = main["points"]
    for k, (route, colour) in enumerate(zip(main["best_plan_routes"], (BLUE, ORANGE))):
        xs, ys = [pts[i]["lon"] for i in route], [pts[i]["lat"] for i in route]
        ax3.plot(xs, ys, color=colour, lw=2, label=f"Van {'AB'[k]} ({len(route) - 2} stops)", zorder=2)
    for p in pts:
        depot = p["id"] == 0
        ax3.scatter(p["lon"], p["lat"], s=70 if depot else 28, color=INK if depot else "white",
                    edgecolor=INK, zorder=3)
        ax3.annotate(p["name"].replace("Depot: ", "Depot\n"), (p["lon"], p["lat"]), fontsize=7, color=INK2,
                     xytext=(4, 3), textcoords="offset points")
    ax3.set_aspect(1 / 0.92)                      # ~cos(22.5 deg) so the map is not stretched
    ax3.set_xlabel("longitude")
    ax3.set_ylabel("latitude")
    ax3.legend(loc="lower right", fontsize=8, frameon=False)
    opt = main["classical_exact"]["length"]
    found = [lbl.replace("\n", " ").split(" fake_")[0].split(" ibm")[0] for lbl, _, r in rows[1:] if r.get("best_length") and r["best_length"] <= opt + 1e-6]
    ax3.set_title(f"Optimal plan: {opt / 1000:.2f} km (classical exact)\n"
                  f"also found in the samples of: {', '.join(found) or 'none'}", fontsize=9, color=INK, loc="left")
    fig.suptitle("Two vans, 10 places in Kolkata, 8 qubits, QAOA p = 1, "
                 f"{main['problem']['shots']:,} shots per run", x=0.01, ha="left", fontsize=11, color=INK)
    fig.savefig(path)
    plt.close(fig)


def route_figure(summary: dict, path) -> None:
    rows = summary["route"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    labels = [f"{r['cities']} cities\n{r['qubits']} qubits, p={r['layers']}" for r in rows]
    x = range(len(rows))
    ax.bar([i - 0.2 for i in x], [r["p_optimal_random"] * 100 for r in rows], width=0.38, color=GREY,
           label="Random guess")
    ax.bar([i + 0.2 for i in x], [r["p_optimal"] * 100 for r in rows], width=0.38, color=BLUE,
           yerr=[r["p_optimal_sd"] * 100 for r in rows], capsize=4,
           error_kw={"ecolor": INK2, "elinewidth": 1}, label="QAOA (ideal simulator)")
    for i, r in enumerate(rows):
        ax.annotate(f"{r['p_optimal'] / r['p_optimal_random']:.0f}x", (i + 0.2, (r["p_optimal"] + r["p_optimal_sd"]) * 100),
                    xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9, color=INK)
    ax.set_xticks(list(x), labels, fontsize=8)
    ax.set_ylim(0, max((r["p_optimal"] + r["p_optimal_sd"]) * 100 for r in rows) * 1.22)   # room for labels
    ax.set_ylabel("chance one shot is the optimal route (%)")
    ax.set_title("Full-route encoding: QAOA beats guessing, but rarely returns the optimum",
                 fontsize=10, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.savefig(path)
    plt.close(fig)


def scaling_figure(summary: dict, path) -> None:
    rows = [r for r in summary["scaling"] if r["n"] <= 14]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for key, label, colour in (("heuristic_seconds", "Heuristic (NN + 2-opt)", BLUE),
                               ("held_karp_seconds", "Held–Karp (exact)", ORANGE),
                               ("brute_seconds", "Brute force (exact)", AQUA)):
        pts = [(r["n"], r[key]) for r in rows if r.get(key)]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="o", ms=5, lw=2, color=colour, label=label)
    ax.set_yscale("log")
    ax.set_xlabel("cities")
    ax.set_ylabel("run time (s, log scale)")
    ax.set_title("Classical solvers on this computer (one map per size, seed 1)",
                 fontsize=10, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(path)
    plt.close(fig)


def make_all(summary: dict) -> list:
    C.FIGURES_DIR.mkdir(exist_ok=True)
    paths = [C.FIGURES_DIR / "main_result.png", C.FIGURES_DIR / "route_qaoa_vs_random.png",
             C.FIGURES_DIR / "classical_scaling.png"]
    main_result_figure(summary, paths[0])
    route_figure(summary, paths[1])
    scaling_figure(summary, paths[2])
    return paths
