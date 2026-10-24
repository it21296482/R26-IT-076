"""Optional machine-readable progress for the application subprocess."""
import json
import os


def report_progress(stage: str, percent: float, **detail) -> None:
    # The Node backend enables this flag and reads the CSE_PROGRESS prefix to
    # update the progress bar. flush=True sends each event without waiting for
    # Python's output buffer. Percent means stage completion, not model accuracy
    # or the probability that a forecast will be correct.
    if os.environ.get("CSE_MARKET_PROGRESS") == "1":
        print("CSE_PROGRESS " + json.dumps({"stage": stage, "percent": percent, **detail}), flush=True)
