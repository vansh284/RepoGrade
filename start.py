"""Start both backend and frontend servers."""

import subprocess
import sys
import os
import signal

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
FRONTEND = os.path.join(ROOT, "frontend")
VENV_PYTHON = os.path.join(ROOT, ".venv", "Scripts", "python.exe")


def main():
    procs = []
    try:
        backend = subprocess.Popen(
            [VENV_PYTHON, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
            cwd=BACKEND,
        )
        procs.append(backend)

        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND,
            shell=True,
        )
        procs.append(frontend)

        print("RepoGrade running:")
        print("  Backend:  http://localhost:8000")
        print("  Frontend: http://localhost:5173")
        print("  Press Ctrl+C to stop")

        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()


if __name__ == "__main__":
    main()
