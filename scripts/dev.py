"""Start both local services; never changes the parent/system environment."""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
python = root / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
npm = 'npm.cmd' if sys.platform == 'win32' else 'npm'
processes = []

def stop(*_):
    for process in processes:
        if process.poll() is None:
            if os.name == 'posix': os.killpg(process.pid, signal.SIGTERM)
            else: process.terminate()
    for process in processes:
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill()

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        processes.append(subprocess.Popen([str(python),'-m','uvicorn','app.main:app','--reload','--host','127.0.0.1','--port','8000'],cwd=root/'backend',start_new_session=(os.name=='posix')))
        processes.append(subprocess.Popen([npm,'run','dev','--','--port','5173','--strictPort'],cwd=root/'frontend',start_new_session=(os.name=='posix')))
        print('CampusOS-XDU: http://127.0.0.1:5173 | API docs: http://127.0.0.1:8000/docs',flush=True)
        while all(process.poll() is None for process in processes): time.sleep(.5)
        sys.exit(next((p.returncode for p in processes if p.poll() is not None),0))
    except KeyboardInterrupt: pass
    finally: stop()
