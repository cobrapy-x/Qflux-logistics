# AI-use note


## Tools used

- **Claude (Anthropic), in the Claude Cowork desktop app.** Planning, most of the Python code,
  debugging, the dashboard, the README.
- **IBM Quantum Platform / Qiskit Runtime:** running the circuit on real hardware.

We reviewed the code, ran every experiment ourselves, and checked results against exact
classical references (`tests/`, 27 checks).

## One thing the AI got wrong, and how we caught it

**The first two-van QUBO optimised the wrong thing.** The AI's first version split the stops
between two vans with a "keep nearby stops together" objective (weighted Max-Cut on
distances), and it had **no capacity rule**. On the simulator, QAOA's best plans were
**14.7% (10 places) and 28.7% (13 places) longer** than the best split.

- **How we caught it:** we compared QAOA's best plan with an exhaustive classical check of
  every possible split, each van routed exactly with Held–Karp. A correct encoding's optimum
  should match that check, and it didn't.
- **Why it happened:** with no capacity limit, the cheapest plan is usually one van doing
  every stop. Taking a shortcut never makes a route longer.
- **Fix:** a capacity penalty (van B takes exactly ⌊k/2⌋ stops) and Clarke–Wright savings as the
  weights. The exhaustive check now finds that QAOA's best sampled plan matches the optimum
  (gap 0.0%). `tests/test_experiments.py` and `tests/test_quantum_hardware.py` keep checking this.

## A second error

**Code that crashed under real use.** The AI's dashboard called Qiskit's compiler from
whichever web-server thread handled the click. Unit tests passed, but an end-to-end browser
test (click "Simulate", then "Submit") crashed the server with a segmentation fault inside
Qiskit's compiled core. Fix: all Qiskit work now runs on one dedicated worker thread
(`src/quantum_hardware/ibm_runner.py`).

## How we verified AI-written code

- `tests/test_quantum_hardware.py::test_circuit_matches_the_simulator`: the Qiskit circuit
  gives the same probabilities as our own simulator, to 6 decimal places.
- `tests/test_quantum_simulation.py`: the QUBO energy of the optimal tour equals its length.
- `tests/test_classical.py`: brute force equals Held–Karp; the heuristic never beats the optimum.
- `tests/test_realmap.py`: with road distances selected, the circuit sent to IBM is built from
  street distances.
