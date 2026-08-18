from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMAGE = "ipost-worker"


def run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="latest")
    parser.add_argument("--push")
    args = parser.parse_args()
    try:
        subprocess.run(["docker", "version"], check=True, capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Docker Desktop must be running")
        raise SystemExit(1)
    run(
        [
            "docker",
            "buildx",
            "build",
            "--platform",
            "linux/amd64",
            "--provenance=false",
            "--sbom=false",
            "--load",
            "-f",
            "apps/worker/Dockerfile",
            "-t",
            f"{IMAGE}:{args.tag}",
            ".",
        ]
    )
    if not args.push:
        print(f"built {IMAGE}:{args.tag}")
        print("next: terraform -chdir=infra output -raw ecr_repository_url")
        print(f"then: uv run python apps/worker/package_docker.py --tag {args.tag} --push <ecr-url>")
        return
    remote = f"{args.push.rstrip('/')}:{args.tag}"
    run(["docker", "tag", f"{IMAGE}:{args.tag}", remote])
    run(["docker", "push", remote])
    print(remote)


if __name__ == "__main__":
    main()
