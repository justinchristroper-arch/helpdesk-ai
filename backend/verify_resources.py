"""Local Linux container memory sample; no external AI calls or load-test claims."""
import json
import os
import resource
from pathlib import Path
from time import perf_counter

os.environ["MINDROUTER_API_KEY"] = ""
os.environ["HF_HUB_OFFLINE"] = "1"

from app.db import Session
from app.embeddings import local_model
from app.semantic import answer


def rss_mib():
    line = next(line for line in Path("/proc/self/status").read_text().splitlines() if line.startswith("VmRSS:"))
    return round(int(line.split()[1]) / 1024, 2)


started = perf_counter()
samples = [{"queries": 0, "rss_mib": rss_mib()}]
with Session() as db:
    for index in range(25):
        result = answer(db, "How do I request VPN access?")
        assert result.outcome == "answered"
        if (index + 1) % 5 == 0:
            samples.append({"queries": index + 1, "rss_mib": rss_mib()})
assert local_model() is local_model()
print(json.dumps({"queries": 25, "seconds": round(perf_counter() - started, 2),
                  "process_peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
                  "samples": samples,
                  "container_memory_limit": Path("/sys/fs/cgroup/memory.max").read_text().strip(),
                  "container_memory_events": Path("/sys/fs/cgroup/memory.events").read_text().splitlines(),
                  "external_generation_calls": 0,
                  "limitation": "25 sequential queries, not a concurrency benchmark or proof of no leaks."}, indent=2))
