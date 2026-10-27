"""Fixed MachineLearning entry for the Lindsey actual-Blender-mesh proof.

Blender sends a hash-bound private snapshot request over stdin. A standalone
main() call uses the fixed fresh snapshot. No command-line options or new
Python environment are used; this process never imports bpy.
"""

import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/street277"


def main(request=None):
    spec = importlib.util.spec_from_file_location(
        "lindsey277_observed_cpu", ROOT / "web/tests/verify_lindsey277.py"
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    if request is None:
        observed = OUT / "observed-fresh.json"
        request = {
            "observedPath": str(observed),
            "observedSha256": verifier.sha(observed),
            "proofPath": str(OUT / "observed-fresh-cpu-verification.json"),
        }
    observed = Path(request["observedPath"]).resolve()
    proof_path = Path(request["proofPath"]).resolve()
    assert observed.parent == OUT and proof_path.parent == OUT
    proof = verifier.verify_observed(observed, request["observedSha256"])
    proof_path.write_text(json.dumps(proof, indent=2) + "\n")
    print("LINDSEY277_ACTUAL_CPU_VERIFIED", request["observedSha256"], flush=True)
    return proof


if __name__ == "__main__":
    payload = "" if sys.stdin.isatty() else sys.stdin.read()
    main(json.loads(payload) if payload.strip() else None)
