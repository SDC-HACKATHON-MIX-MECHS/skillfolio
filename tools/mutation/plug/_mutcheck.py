"""Shared mutation applier. A mutation is (old, new) or (old, new, count): the target text must occur
exactly once (or exactly `count` times, for constants deliberately replaced at every use). A mutation whose
target text is missing, occurs a different number of times, or whose
mutated source fails to compile/exec is a HARNESS PROBLEM, never a kill: it exits the process with
HARNESS_RC (97), which run_all.sh reports as a harness problem (pytest's own "tests failed" code is 1)."""

import os
import sys

HARNESS_RC = 97


def problem(module, mutants, name):
    """Return a description of what is wrong with mutant `name`, or None if it is applicable."""
    old, new, *rest = mutants[name]
    want = rest[0] if rest else 1
    src = open(module.__file__, encoding="utf-8").read()
    n = src.count(old)
    if n != want:
        return f"{name}: target occurs {n} times in {os.path.basename(module.__file__)} (declared: exactly {want})"
    if old == new:
        return f"{name}: replacement equals target"
    try:
        compile(src.replace(old, new), module.__file__, "exec")
    except SyntaxError as e:
        return f"{name}: mutated source does not compile ({e})"
    return None


def apply(module, mutants, name):
    msg = problem(module, mutants, name)
    if msg is None:
        old, new = mutants[name][:2]
        src = open(module.__file__, encoding="utf-8").read()
        try:
            exec(compile(src.replace(old, new), module.__file__, "exec"), module.__dict__)
            return
        except Exception as e:  # noqa: BLE001 - any failure to load the mutant is a harness problem
            msg = f"{name}: mutant failed to load ({type(e).__name__}: {e})"
    sys.stderr.write(f"HARNESS PROBLEM: {msg}\n")
    sys.stderr.flush()
    os._exit(HARNESS_RC)


def check_all(module, mutants):
    """Print every harness problem and return how many there were."""
    bad = [m for m in (problem(module, mutants, n) for n in mutants) if m]
    for m in bad:
        print("HARNESS PROBLEM:", m)
    return len(bad)


def check_plug(plug):
    """Entry point for run_all.sh: number of harness problems in a plug module."""
    return check_all(plug.TARGET, plug.MUTANTS)
