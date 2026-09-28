"""Scan Git-visible text for token patterns and exact local secret values; never print values."""
import json
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "-c", f"safe.directory={root.as_posix()}", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True).splitlines()
secrets = []
for env in (root / ".env", root / "backend/.env", root / "frontend/.env.local"):
    if not env.exists():
        continue
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        if any(term in key for term in ("PASSWORD", "SECRET", "API_KEY", "TOKEN")) and len(value.strip()) >= 12:
            secrets.append(value.strip().strip('\"\''))
for name in (".demo-credentials.json", ".deployment-secrets.json"):
    path = root / name
    if path.exists():
        def collect(obj):
            if isinstance(obj, dict):
                for k,v in obj.items():
                    if isinstance(v, str) and any(x in k.lower() for x in ("password", "secret", "token")) and len(v) >= 12:
                        secrets.append(v)
                    collect(v)
        collect(json.loads(path.read_text(encoding="utf-8-sig")))
patterns = [r"sk[-_][A-Za-z0-9_-]{24,}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
hits = []
bundles = [str(p.relative_to(root)) for p in (root / "frontend/dist").rglob("*") if p.is_file()]
for name in files + bundles:
    path = root / name
    if not path.is_file():
        continue
    data = path.read_bytes().decode("utf-8-sig", errors="replace")
    if any(secret in data for secret in secrets) or any(re.search(pattern, data) for pattern in patterns):
        hits.append(name)
history_match = None
if "--history" in sys.argv:
    history = subprocess.check_output(["git", "-c", f"safe.directory={root.as_posix()}",
                                      "log", "--all", "-p", "--format="], cwd=root).decode("utf-8", errors="replace")
    history_match = any(secret in history for secret in secrets) or any(re.search(pattern, history) for pattern in patterns)
print(json.dumps({"git_visible_files": len(files), "frontend_bundle_files": len(bundles), "potential_secret_files": hits, "known_local_values_checked": len(secrets), "history_match": history_match}))
raise SystemExit(bool(hits) or bool(history_match))
