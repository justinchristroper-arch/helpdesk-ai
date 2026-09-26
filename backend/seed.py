"""Upload synthetic files through the real authenticated ingestion API."""
import getpass
import os
from pathlib import Path

import httpx


def main():
    base = os.environ.get("API_URL", "http://localhost:8000")
    email = input("Admin email: ")
    password = getpass.getpass("Admin password: ")
    with httpx.Client(base_url=base, timeout=180) as client:
        login = client.post("/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        client.headers["Authorization"] = "Bearer " + login.json()["token"]
        existing = client.get("/documents")
        existing.raise_for_status()
        filenames = {d["filename"] for d in existing.json()}
        for path in sorted((Path(__file__).parent.parent / "sample-data").glob("*.md")):
            if path.name in filenames:
                print("Already indexed:", path.name)
                continue
            with path.open("rb") as file:
                response = client.post("/documents", files={"file": (path.name, file, "text/markdown")})
            if response.status_code == 429:
                raise SystemExit("Upload rate limit reached. Wait one minute and rerun; indexed files are skipped.")
            response.raise_for_status()
            print("Indexed:", path.name)


if __name__ == "__main__":
    main()
