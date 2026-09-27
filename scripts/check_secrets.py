"""Scan Git-visible text for token patterns and exact local secret values; never print values."""
import json
import pathlib
import re
import subprocess

root = pathlib.Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "-c", f"safe.directory={root.as_posix()}", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True).splitlines()
secrets = []
env = root / ".env"
if env.exists():
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        if any(term in key for term in ("PASSWORD", "SECRET", "API_KEY")) and len(value.strip()) >= 12:
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
patterns = [r"sk-[A-Za-z0-9]{24,}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"]
hits = []
for name in files:
    path = root / name
    if not path.is_file() or path.stat().st_size > 2_000_000:
        continue
    try:
        data = path.read_text(encoding="utf-8-sig")
    except UnicodeError:
        continue
    if any(secret in data for secret in secrets) or any(re.search(pattern, data) for pattern in patterns):
        hits.append(name)
print(json.dumps({"git_visible_files": len(files), "potential_secret_files": hits, "known_local_values_checked": len(secrets)}))
raise SystemExit(bool(hits))
