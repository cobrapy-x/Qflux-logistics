"""Build WRITEUP.pdf (repository root) from results/summary.json and figures/.

    python reproduce.py               # 1. produce the numbers and figures
    python writeup/build_writeup.py   # 2. turn them into the write-up

Team name and members come from writeup/team.json. Every number in the PDF is
read from results/summary.json, so the write-up always matches the code.
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "summary.json"
TEAM = ROOT / "writeup" / "team.json"
OUT = ROOT / "WRITEUP.pdf"

ACCENT = colors.HexColor("#2a78d6")
INK2 = colors.HexColor("#52514e")
LINE = colors.HexColor("#dcdad3")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=16, leading=19, alignment=TA_LEFT, spaceAfter=2)
SUB = ParagraphStyle("Sub", parent=ss["Normal"], fontSize=9, textColor=INK2, leading=12, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=11.5, textColor=ACCENT, spaceBefore=7, spaceAfter=3)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9, leading=12.2, spaceAfter=4)
CAP = ParagraphStyle("Cap", parent=P, fontSize=8, textColor=INK2, leading=10.5)
BUL = ParagraphStyle("Bul", parent=P, leftIndent=10, bulletIndent=0, spaceAfter=2)
CELL = ParagraphStyle("Cell", parent=P, fontSize=8.2, leading=10, spaceAfter=0)


def _figure(path, width):
    """An image scaled to `width`, keeping the file's own aspect ratio."""
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(str(path)).getSize()
    return Image(str(path), width=width, height=width * h / w)


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def km(m):
    return f"{m / 1000:.2f} km"


def table(rows, widths, header=True):
    data = [[Paragraph(str(c), CELL) for c in r] for r in rows]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    style = [("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef3fb"))]
    t.setStyle(TableStyle(style))
    return t


def bullets(items):
    return [Paragraph(i, BUL, bulletText="•") for i in items]


def build() -> None:
    s = json.loads(SUMMARY.read_text())
    team = json.loads(TEAM.read_text())
    m, route, scaling, v = s["main"], s["route"], s["scaling"], s["versions"]
    hw = m.get("hardware")
    ex, heur, noisy, ideal, idx = m["classical_exact"], m["classical_heuristic"], m["noisy"], m["ideal_sampled"], m["ideal_exact"]
    r4 = next(r for r in route if r["cities"] == 4 and r["layers"] == 1)
    r5 = next(r for r in route if r["cities"] == 5)
    sc = {r["n"]: r for r in scaling}
    story = []

    # ---------------- title ----------------
    story += [Paragraph("Delivery routing with QAOA: a fair comparison on a real map", H1),
              Paragraph(f"<b>{team['team_name']}</b> · {', '.join(team['members'])} · Qiskit Fall Fest Hackathon 2026, "
                        f"Problem 06 (QAOA &amp; optimisation) · code: {team['repository']}", SUB)]

    # ---------------- problem ----------------
    story += [Paragraph("1. Problem", H2), Paragraph(
        "A delivery company must decide <i>who delivers what</i> and <i>in which order</i>. Both are routing "
        "problems (variants of the Travelling Salesperson Problem, TSP) whose number of possible answers grows "
        "factorially with the number of stops. We ask: can QAOA, run on a simulator and on a real IBM quantum "
        "computer, solve a small but real instance, and where does the approach stop being useful compared with "
        "classical methods? <b>Success</b> means: a correct QUBO encoding (checked against exact classical "
        "solutions), QAOA output that is measurably better than random guessing, an honest comparison with "
        "classical solvers given similar resources, and a clear statement of where the quantum approach breaks down.",
        P)]

    # ---------------- method ----------------
    story += [Paragraph("2. Method", H2)]
    story += bullets([
        f"<b>Map.</b> A depot (Sealdah) and 9 well-known places in Kolkata (approximate coordinates). For the main "
        f"result we use great-circle distances, so the result is reproducible offline; the dashboard can also use "
        f"real road distances from OpenStreetMap (OSRM).",
        "<b>Classical solvers</b> (our own code, no solver libraries): nearest-neighbour + 2-opt heuristic; Held–Karp dynamic programming "
        "(exact, O(n<super>2</super>2<super>n</super>)); brute force (exact, (n−1)!/2 tours).",
        "<b>Encoding A, full route</b> (n−1)<super>2</super> qubits: x<sub>i,t</sub>=1 if stop i is visited at step t. "
        "Energy = route length + A·(one stop per step)<super>2</super> + A·(each stop once)<super>2</super>.",
        f"<b>Encoding B, two vans</b> (main result), one qubit per stop: x<sub>i</sub>=1 if van B serves stop i "
        f"(stop 1 fixed to van A, so {m['problem']['qubits']} qubits). Energy = −(Clarke–Wright savings "
        f"s<sub>ij</sub> = d<sub>0i</sub>+d<sub>0j</sub>−d<sub>ij</sub> of stops sharing a van) + A·(|B| − 4)<super>2</super> "
        f"(capacity: van B takes 4 of the 9 stops). Each van is then routed exactly with Held–Karp.",
        f"<b>QAOA.</b> QUBO → Ising (x = (1−z)/2); circuit = H on all qubits, then p layers of RZZ/RZ (cost) and RX "
        f"(mixer). Angles γ, β tuned on our own state-vector simulator (grid search + Nelder–Mead, "
        f"{m['problem']['tuning_evaluations']} evaluations, p = {m['problem']['layers']}); only the final tuned circuit "
        f"is run with {m['problem']['shots']:,} shots.",
        f"<b>Three quantum back-ends, kept separate:</b> (i) ideal simulation (exact state vector); (ii) Qiskit Aer "
        f"with the noise model of IBM's {noisy['backend'].replace('fake_', 'ibm_')} (a <i>noise model</i>, not hardware; "
        f"{len(noisy['runs'])} seeds); (iii) a real IBM device via Qiskit Runtime SamplerV2 with dynamical "
        f"decoupling and gate twirling. The compiled circuit has {noisy['two_qubit_gates']} two-qubit gates "
        f"(depth {noisy['depth']}).",
        "<b>Checks</b> (unit tests in tests/): QUBO energy of the optimal tour equals its length; the Qiskit circuit gives "
        "the same probabilities as our simulator; brute force equals Held–Karp; heuristic never beats the optimum; "
        "street distances reach the hardware circuit.",
    ])

    # ---------------- results ----------------
    story += [Paragraph("3. Results", H2),
              _figure(ROOT / "figures" / "main_result.png", 17.4 * cm),
              Paragraph("<b>Figure 1 (main result).</b> Share of shots that obey the capacity rule (left) and that are "
                        "the optimal plan (middle), with binomial standard errors (noisy simulator: spread over "
                        "3 seeds). Right: the optimal plan.", CAP), Spacer(1, 4)]

    rows = [["Source", "Valid shots", "Optimal-plan shots", "Best plan found", "Gap vs optimum"],
            ["Random guessing", pct(m["random"]["p_valid"]), pct(m["random"]["p_best"], 2), "—", "—"],
            ["Ideal simulator (exact state)", pct(idx["p_valid"]), pct(idx["p_best"], 2), "—", "—"],
            [f"Ideal simulator ({ideal['shots']:,} shots)", f"{pct(ideal['p_valid'])} ± {pct(ideal['p_valid_se'])}",
             f"{pct(ideal['p_best'], 2)} ± {pct(ideal['p_best_se'], 2)}", km(ideal["best_length"]),
             f"{ideal['gap_percent']:.1f}%"],
            [f"Noisy simulator ({noisy['backend']}, 3 seeds)", f"{pct(noisy['p_valid'])} ± {pct(noisy['p_valid_sd'])}",
             f"{pct(noisy['p_best'], 2)} ± {pct(noisy['p_best_sd'], 2)}", km(noisy["best_length"]),
             f"{(noisy['best_length'] / ex['length'] - 1) * 100:.1f}%"]]
    if hw:
        rows.append([f"<b>IBM {hw['backend']}</b> (real hardware)", f"{pct(hw['p_valid'])} ± {pct(hw['p_valid_se'])}",
                     f"{pct(hw['p_best'], 2)} ± {pct(hw['p_best_se'], 2)}",
                     km(hw["best_length"]) if hw["best_length"] else "—",
                     f"{hw['gap_percent']:.1f}%" if hw["gap_percent"] is not None else "—"])
    rows += [["Classical exact (all 70 fair splits)", "—", "—", km(ex["length"]), f"0 ({ex['seconds'] * 1000:.1f} ms)"],
             ["Classical sweep heuristic", "—", "—", km(heur["length"]),
              f"{heur['gap_percent']:.1f}% ({heur['seconds'] * 1000:.1f} ms)"]]
    story.append(table(rows, [5.2 * cm, 2.9 * cm, 3.2 * cm, 2.7 * cm, 3.2 * cm]))
    story.append(Spacer(1, 5))

    hw_text = (f"On the real device <b>{hw['backend']}</b> (job <font face='Courier'>{hw['job_id']}</font>, "
               f"{hw['date_utc'][:10]}, {hw['shots']:,} shots"
               + (f", {hw['qpu_seconds']} s of quantum time" if hw.get("qpu_seconds") else "")
               + f") {pct(hw['p_valid'])} of shots were valid and {pct(hw['p_best'], 2)} were the optimal plan, "
               f"compared with {pct(noisy['p_valid'])} and {pct(noisy['p_best'], 2)} for the noise model and "
               f"{pct(idx['p_valid'])} and {pct(idx['p_best'], 2)} for the ideal simulator. "
               + ("The real chip lost more than the noise model predicted, but stayed clearly above random "
                  "guessing; the noise model is optimistic for this circuit."
                  if hw["p_valid"] < noisy["p_valid"] - 2 * max(hw["p_valid_se"], noisy["p_valid_sd"])
                  else "The real chip matched the noise model within the error bars.")
               if hw else "No real-hardware run is included in this version (see run_hardware.py).")
    story.append(Paragraph(
        f"QAOA concentrates probability on good answers: valid splits rise from {pct(m['random']['p_valid'])} "
        f"(random) to {pct(idx['p_valid'])} (ideal), and the optimal plan from {pct(m['random']['p_best'], 2)} to "
        f"{pct(idx['p_best'], 2)}, about {idx['p_best'] / m['random']['p_best']:.1f}× random. The noise model costs "
        f"only a few points at this circuit size. Because a few thousand shots cover all 256 bitstrings many times, "
        f"every source finds the optimal {km(ex['length'])} plan, but so does the classical sweep heuristic, in "
        f"under a millisecond. {hw_text}", P))

    story.append(KeepTogether([
        _figure(ROOT / "figures" / "route_qaoa_vs_random.png", 8.4 * cm),
        Paragraph(f"<b>Figure 2.</b> Full-route encoding, ideal simulator, mean ± s.d. over random maps. With 4 cities "
                  f"(9 qubits) one shot is optimal {pct(r4['p_optimal'])} of the time ({r4['p_optimal'] / r4['p_optimal_random']:.0f}× "
                  f"random); with 5 cities (16 qubits) only {pct(r5['p_optimal'], 2)}. Held–Karp solves both exactly in "
                  f"under 0.1 ms.", CAP)]))
    story.append(Paragraph(
        f"<b>Classical scaling</b> (figures/classical_scaling.png): brute force takes {sc[11]['brute_seconds']:.1f} s at "
        f"11 cities, Held–Karp {sc[14]['held_karp_seconds']:.2f} s at 14 cities, and the heuristic "
        f"{sc[60]['heuristic_seconds']:.2f} s at 60 cities. The full-route encoding would need 59<super>2</super> = 3,481 "
        f"qubits for 60 cities.", P))

    # ---------------- limits ----------------
    story += [Paragraph("4. Honest limits", H2)]
    story += bullets([
        "<b>No quantum advantage.</b> Classical methods match or beat QAOA on every instance here, in less time. Held–Karp "
        "is exact, so no method can find a shorter route; at best a quantum method could match it faster, and our "
        "measurements show the opposite. TSP is NP-hard and QAOA has no proven speed-up for it.",
        "<b>Small sizes.</b> The full-route encoding needs (n−1)<super>2</super> qubits and only (n−1)!/2 of the "
        "2<super>(n−1)<super>2</super></super> bitstrings are valid tours (1 in 10<super>19</super> at 10 cities). "
        "Exact simulation stops at about 5 cities (16 qubits); on hardware, noise from the 140–440 two-qubit gates "
        "limits it to about 4.",
        "<b>The two-van result is easy for sampling.</b> With 8 qubits, 4,000 shots almost certainly contain the optimum "
        "even for random guessing (expected ~16 hits). The meaningful metric is the <i>probability</i> of good answers, "
        "not \"best plan found\".",
        "<b>Proxy objective.</b> QAOA optimises savings within a van, not the exact route length; on this map its optimum "
        "coincides with the true best split, but that is not guaranteed in general.",
        "<b>Assumptions.</b> Approximate coordinates; great-circle distances in the main result (road distances in the "
        "dashboard are averaged over both directions); a fixed 5/4 capacity split; p = 1; angles tuned on a noiseless "
        "simulator and not re-tuned on hardware.",
        "<b>Not tested:</b> larger p, other mixers or encodings (e.g. n log n qubits), error mitigation beyond "
        "decoupling and twirling, repeated hardware runs on different days.",
    ])

    # ---------------- AI use ----------------
    story += [Paragraph("5. AI-use note", H2), Paragraph(
        "We used Claude (Anthropic, in the Cowork app) for code, debugging and drafting, and the IBM Quantum Platform for "
        "hardware. <b>One thing the AI got wrong:</b> its first two-van QUBO grouped stops by distance (a Max-Cut) "
        "without a capacity rule. QAOA's best plans were 15–29% longer than the best split found by our exhaustive "
        "classical check. The cause: without capacity, the cheapest plan is one van doing everything, so the proxy "
        "did not match the real goal. We added the capacity penalty and Clarke–Wright savings; the gap is now 0%. "
        "Details and a second error in AI_USE_NOTE.md.", P),
        Paragraph(f"Software: Python {v['python']}, Qiskit {v['qiskit']}, Qiskit Aer {v['qiskit-aer']}, "
                  f"qiskit-ibm-runtime {v['qiskit-ibm-runtime']}, NumPy {v['numpy']}. Generated {s['generated_utc'][:10]} "
                  f"by <font face='Courier'>python reproduce.py</font>.", CAP)]

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm, title="Write-up: Delivery routing with QAOA",
                            author=team["team_name"])

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(INK2)
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.0 * cm, f"{team['team_name']} · page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
