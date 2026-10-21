#!/usr/bin/env python
"""One-command launcher: python run.py

Does everything on a new computer: finds the licence file, creates a private .venv, installs the
requirements (with retries), downloads the model weights, trains the model and opens the app in the
browser. Later runs start in a few seconds. Every step prints what it does; if something cannot be done
automatically it says why and what to do.

    python run.py                    start the app (http://localhost:8501)
    python run.py --port 9000        other port
    python run.py --no-browser       do not open a browser tab
    python run.py --rebuild          retrain the model from dataset_curated/
    python run.py --make-offline-bundle   download all packages into ./wheels (for computers without internet)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
WHEELS = ROOT / "wheels"
LOG = ROOT / "outputs" / "setup_log.txt"
REQUIRED_MODULES = ["numpy", "pandas", "PIL", "sklearn", "skimage", "joblib", "cryptography", "torch", "torchvision", "open_clip", "transformers", "streamlit"]
CONTACT = "Shahul Hameed.S - shahul@getwebsite.today"
NEED_FREE_GB = 6                                   # packages (PyTorch) + model weights + working space

os.environ.setdefault("PYTHONUTF8", "1")           # no encoding errors on Windows consoles
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("PYTHONWARNINGS", "ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ------------------------------------------------------------------ output helpers
def say(msg: str) -> None:
    print(f"[run] {msg}", flush=True)


def _own_console() -> bool:
    """True when Windows opened this console only for us (double-click), so it would vanish on exit."""
    if "LIPOMA_OWN_CONSOLE" in os.environ:               # decided once by the first process (children share the console)
        return os.environ["LIPOMA_OWN_CONSOLE"] == "1"
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        pids = (ctypes.c_uint * 8)()
        return ctypes.windll.kernel32.GetConsoleProcessList(pids, 8) <= 2
    except Exception:
        return False


os.environ.setdefault("LIPOMA_OWN_CONSOLE", "1" if _own_console() else "0")


def die(problem: str, *todo: str) -> None:
    """Stop with a clear message: what went wrong and what to do about it."""
    print("\n" + "=" * 72, flush=True)
    print("  The platform could not start.", flush=True)
    print(f"  {problem}", flush=True)
    for t in todo:
        print(f"  - {t}", flush=True)
    print(f"  Details: {LOG}   Help: {CONTACT}", flush=True)
    print("=" * 72, flush=True)
    if _own_console():
        try:
            input("\nPress Enter to close this window ...")
        except Exception:
            pass
    sys.exit(1)


def log(text: str) -> None:
    try:
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(text)
    except OSError:
        pass


def run_logged(cmd: list[str], env: dict | None = None, quiet: bool = False) -> tuple[int, str]:
    """Run a command, show its output, keep it in the log, return (exit code, last 60 lines)."""
    log(f"\n$ {' '.join(map(str, cmd))}\n")
    full_env = {**os.environ, **(env or {})}
    tail: list[str] = []
    try:
        p = subprocess.Popen([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", cwd=ROOT, env=full_env)
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    try:
        for line in p.stdout:
            if not quiet:
                print(line, end="", flush=True)
            log(line)
            tail.append(line)
            del tail[:-60]
        p.wait()
    except KeyboardInterrupt:
        p.kill()
        raise
    return p.returncode, "".join(tail)


# ------------------------------------------------------------------ checks before anything is installed
def check_python() -> None:
    if sys.version_info < (3, 10):
        die(f"Python 3.10 or newer is required (this is {sys.version.split()[0]}).",
            "Install the latest Python from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), then run again.")
    if sys.maxsize <= 2 ** 32:
        die("This is a 32-bit Python; the machine-learning packages need 64-bit Python.",
            "Install the 64-bit Python from https://www.python.org/downloads/ and run again.")


def check_folder() -> None:
    low = str(ROOT).lower()
    if ".zip" in low or "\\appdata\\local\\temp\\" in low or "/tmp/" in low:
        die("The project is being run from inside a zip file or a temporary folder.",
            "Extract (Extract All) the whole zip to a normal folder such as Documents, open that folder, and run again.")
    for rel in ("app.py", "requirements.txt", "scripts/train.py", "lipoma_proto/licence.py", "lipoma_proto/licence_public_key.pem",
                "dataset_curated/images.vault", "dataset_curated/metadata.csv"):
        if not (ROOT / rel).exists():
            die(f"The project folder is incomplete: '{rel}' is missing.",
                "Download the project again completely (green 'Code' button > Download ZIP, then extract all) and keep the licence file.")
    vault = ROOT / "dataset_curated" / "images.vault"
    if vault.stat().st_size < 1000:
        die("dataset_curated/images.vault is not the real file (it looks like a download placeholder).",
            "Download the project as a ZIP from GitHub (not a partial copy) and extract it again.")
    try:
        LOG.parent.mkdir(exist_ok=True)
        probe = LOG.parent / ".write_test"
        probe.write_text("x")
        probe.unlink()
    except OSError:
        die("This folder is read-only, so the platform cannot save its files here.",
            "Move the project folder to Documents (not Program Files, not a read-only or network drive) and run again.")


def check_disk(need_gb: float) -> None:
    free = shutil.disk_usage(ROOT).free / 1e9
    if free < need_gb:
        die(f"Not enough free disk space ({free:.1f} GB free, about {need_gb:.0f} GB needed).",
            "Free some space on this drive (or move the project to a drive with more space) and run again.")


def find_licence() -> None:
    """A licence file must be in the project folder. If it is not, look in the usual download places or ask for it."""
    sys.path.insert(0, str(ROOT))
    if list(ROOT.glob("*.licence*")) or os.environ.get("LIPOMA_LICENCE"):
        return
    home = Path.home()
    found: list[Path] = []
    for d in (home / "Downloads", home / "Desktop", home / "Documents", ROOT.parent):
        try:
            found += [p for p in d.glob("*.licence*") if p.is_file() and p.stat().st_size < 20000]
        except OSError:
            pass
    found = sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)
    if found:
        shutil.copy2(found[0], ROOT / found[0].name)
        say(f"licence file found in {found[0].parent} - copied into the project folder")
        return
    if sys.stdin and sys.stdin.isatty():
        print("\nNo licence file found. It is the file you received by e-mail (its name ends with .licence).", flush=True)
        print("Drag that file into this window (or type its full path) and press Enter.", flush=True)
        try:
            answer = input("Licence file: ").strip().strip('"').strip("'")
        except (EOFError, KeyboardInterrupt):
            answer = ""
        src = Path(answer).expanduser() if answer else None
        if src and src.is_file():
            shutil.copy2(src, ROOT / src.name)
            say("licence file copied into the project folder")
            return
    die("No licence file found.",
        f"Save the licence file you received by e-mail (its name ends with .licence) inside this folder: {ROOT}",
        "Then run this again.")


# ------------------------------------------------------------------ environment
def requirements_stamp() -> str:
    return hashlib.sha256((ROOT / "requirements.txt").read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def missing_modules() -> list[str]:
    return [m for m in REQUIRED_MODULES if importlib.util.find_spec(m) is None]


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if sys.platform.startswith("win") else "bin/python")


def env_ready() -> bool:
    stamp = VENV / ".requirements_ok"
    return stamp.exists() and stamp.read_text().strip() == requirements_stamp()


def pip_hint(tail: str) -> list[str]:
    t = tail.lower()
    hints = []
    if "no matching distribution" in t or "could not find a version" in t:
        hints.append("No matching package for this Python. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ "
                     "(64-bit), delete the .venv folder and run again.")
    if "no space left" in t or "errno 28" in t:
        hints.append("The disk is full. Free some space and run again.")
    if "winerror 206" in t or "filename or extension is too long" in t or "long path" in t:
        hints.append("The folder path is too long for Windows. Move the project to a short path such as C:\\lipoma and run again.")
    if "permission" in t or "access is denied" in t or "winerror 5" in t:
        hints.append("Windows blocked a file (antivirus or a program holding it). Close other programs, pause the antivirus "
                     "for a few minutes, delete the .venv folder and run again.")
    if any(k in t for k in ("timed out", "timeout", "connection", "name or service", "getaddrinfo", "ssl", "proxy", "hash")):
        hints.append("The internet connection failed or is blocked (network, proxy, firewall or VPN). Check the connection "
                     "(try another network or a mobile hotspot) and run again - it continues where it stopped.")
    if "microsoft visual c++" in t or "build tools" in t:
        hints.append("A package needed a C++ compiler because no ready-made package exists for this Python. "
                     "Install Python 3.11 or 3.12 (64-bit) and delete the .venv folder.")
    return hints


def pip_install(py: str) -> None:
    """Install requirements; retried (fresh downloads from the second try) because slow links often cut a download."""
    base = [py, "-m", "pip", "install", "--disable-pip-version-check", "--progress-bar", "off",
            "--default-timeout=120", "--retries", "10", "-r", str(ROOT / "requirements.txt")]
    if WHEELS.exists() and any(WHEELS.iterdir()):
        say("offline package bundle found - installing without internet")
        base += ["--no-index", "--find-links", str(WHEELS)]
    tail = ""
    for attempt in range(1, 4):
        cmd = base + (["--no-cache-dir"] if attempt > 1 else [])
        rc, tail = run_logged(cmd)
        if rc == 0:
            return
        if attempt < 3:
            say(f"installation was interrupted (attempt {attempt} of 3) - trying again in 5 seconds ...")
            time.sleep(5)
    die("The packages could not be installed.", *(pip_hint(tail) or ["Check the internet connection and run again - it continues where it stopped."]))


def verify_imports(py: str) -> str:
    """Empty string if every required package imports, else the error text."""
    code = "import " + ", ".join(REQUIRED_MODULES)
    rc, out = run_logged([py, "-W", "ignore", "-c", code])
    return "" if rc == 0 else out


def install_into_venv(py: str) -> None:
    say("installing the required packages (first run only; about 3 GB, usually 5-15 minutes) ...")
    check_disk(NEED_FREE_GB)
    pip_install(py)
    err = verify_imports(py)
    if err:
        say("a package did not load correctly - reinstalling it once ...")
        run_logged([py, "-m", "pip", "install", "--disable-pip-version-check", "--progress-bar", "off", "--no-cache-dir",
                    "--force-reinstall", "-r", str(ROOT / "requirements.txt")]
                   + (["--no-index", "--find-links", str(WHEELS)] if WHEELS.exists() and any(WHEELS.iterdir()) else []))
        err = verify_imports(py)
    if err:
        die("The packages were installed but do not start on this computer.",
            *(pip_hint(err) or ["Install Python 3.11 or 3.12 (64-bit) from https://www.python.org/downloads/, delete the .venv folder and run again."]))
    (VENV / ".requirements_ok").write_text(requirements_stamp())


def make_venv() -> None:
    py = venv_python()
    if py.exists():
        rc, _ = run_logged([str(py), "-c", "import sys"])
        if rc == 0:
            return
        say("the .venv folder does not work on this computer (copied from another one?) - recreating it ...")
        shutil.rmtree(VENV, ignore_errors=True)
        if VENV.exists():
            die("The old .venv folder could not be removed.", f"Delete the folder {VENV} by hand and run again.")
    say("creating a private environment in .venv ...")
    rc, tail = run_logged([sys.executable, "-m", "venv", str(VENV)])
    if rc != 0 or not py.exists():
        shutil.rmtree(VENV, ignore_errors=True)
        if "ensurepip" in tail or "python3-venv" in tail or "No module named venv" in tail:
            die("This Python has no 'venv' module.", "On Ubuntu/Debian run: sudo apt install python3-venv python3-pip   then run again.")
        die("The private environment could not be created.",
            "Install Python from https://www.python.org/downloads/ (the full installer, 64-bit) and run again.")
    run_logged([str(py), "-m", "pip", "install", "--disable-pip-version-check", "--progress-bar", "off", "--upgrade", "pip"])


def ensure_environment(argv: list[str]) -> None:
    """Make sure everything is installed (inside .venv), then continue there."""
    inside_venv = Path(sys.prefix).resolve() == VENV.resolve()
    if inside_venv:
        if not env_ready() or missing_modules():
            install_into_venv(sys.executable)
        return
    if not VENV.exists() and not missing_modules():
        return                                         # this Python already has everything: use it
    make_venv()
    if not env_ready() or verify_imports(str(venv_python())):
        install_into_venv(str(venv_python()))
    try:
        rc = subprocess.call([str(venv_python()), str(Path(__file__).resolve()), *argv])
    except KeyboardInterrupt:
        rc = 0
    sys.exit(rc)


# ------------------------------------------------------------------ licence, model, app
def ensure_licence() -> None:
    """Check the licence and that it opens the encrypted dataset."""
    sys.path.insert(0, str(ROOT))
    from lipoma_proto import licence
    licence.remove_plain()                               # leftovers of a run that was killed
    try:
        lic = licence.load_licence()
    except licence.LicenceError as exc:
        licence.lock_local_copy()
        die(f"Licence problem: {exc}")
    try:
        n = len(licence.dataset_files())                 # decrypted into memory
    except licence.LicenceError as exc:
        die(f"Licence problem: {exc}")
    except Exception as exc:
        die(f"The licence could not open the data ({type(exc).__name__}).",
            "Use the original licence file you received, and download the project again completely.")
    say(f"dataset opened in memory ({n} images)")
    say(f"licensed to {lic.name} <{lic.email}> - valid until {lic.expires} ({lic.days_left} days left)")


def model_is_usable() -> bool:
    sys.path.insert(0, str(ROOT))
    from lipoma_proto import config
    if not config.MODEL_FILE.exists():
        return False
    try:
        import sklearn
        from lipoma_proto import licence
        b = licence.load_model(config.MODEL_FILE)
        return b.get("sklearn_version") == sklearn.__version__ and b.get("backbone") == config.BACKBONE
    except Exception as exc:  # incompatible pickle, damaged file ...
        say(f"saved model cannot be loaded here ({type(exc).__name__}) - it will be rebuilt")
        return False


def fetch_weights() -> None:
    """Make sure the BiomedCLIP weights are in models/hf: loaded for real, retried, with a clear message if the internet is blocked."""
    probe = "from lipoma_proto.features import FeatureExtractor; FeatureExtractor(); print('weights ok')"
    rc, _ = run_logged([sys.executable, "-W", "ignore", "-c", probe], env={"HF_HUB_OFFLINE": "1"}, quiet=True)   # already complete: no internet
    if rc == 0:
        return
    check_disk(2)
    say("downloading the model weights (about 800 MB, first run only) ...")
    tail = ""
    for attempt in range(1, 6):
        rc, tail = run_logged([sys.executable, "-W", "ignore", "-c", probe], env={"HF_HUB_OFFLINE": "0"})
        if rc == 0:
            return
        if attempt < 5:
            say(f"download interrupted (attempt {attempt} of 5) - trying again in {5 * attempt} seconds ...")
            time.sleep(5 * attempt)
    die("The model weights could not be downloaded from huggingface.co.",
        "Check the internet connection (a school/college network, proxy, firewall or VPN may block huggingface.co) and run again; "
        "it continues where it stopped.",
        "Try another network or a mobile hotspot.")


def ensure_model(force: bool) -> None:
    sys.path.insert(0, str(ROOT))
    if force or not model_is_usable():
        fetch_weights()
        say("training the model (about 5-15 minutes on the first run; do not close this window) ...")
        tail = ""
        for attempt in range(1, 3):
            rc, tail = run_logged([sys.executable, ROOT / "scripts" / "train.py"])
            if rc == 0:
                return
            if attempt == 1:
                say("training stopped - trying once more ...")
        low = tail.lower()
        if "memory" in low or "killed" in low:
            die("The computer ran out of memory while training.", "Close other programs (browser tabs, etc.) and run again.")
        die("The model could not be trained.", "Run again; if it repeats, send the file below to the developer.")
    else:
        say("trained model found")


def guard_plain_images(remove) -> None:
    """Remove the plain images also when the terminal window is closed, the user logs off or the system shuts down."""
    import atexit
    atexit.register(remove)
    if sys.platform.startswith("win"):
        import ctypes

        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)
        def handler(event):                              # CTRL_C, CTRL_BREAK, CLOSE, LOGOFF, SHUTDOWN
            remove()
            return 0                                     # let the default handling continue
        guard_plain_images.handler = handler             # keep a reference
        ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)
    else:
        import signal
        for sig in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda *_: (remove(), sys.exit(0)))


def port_free(port: int) -> bool:
    for host in ("127.0.0.1", ""):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                return False
    return True


def pick_port(wanted: int) -> int:
    for port in range(wanted, wanted + 30):
        if port_free(port):
            if port != wanted:
                say(f"port {wanted} is busy - using {port} instead")
            return port
    die(f"No free port found near {wanted}.", "Close other programs or run: python run.py --port 9100")
    return wanted


RUNNING = ROOT / "outputs" / ".running"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, 0, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259                                        # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def already_running(no_browser: bool) -> None:
    """A second 'python run.py' must not start a second copy (it would remove the first copy's sample images)."""
    try:
        pid, port = map(int, RUNNING.read_text().split())
    except (OSError, ValueError):
        return
    if pid != os.getpid() and pid_alive(pid):
        say(f"the platform is already running: http://localhost:{port}")
        if not no_browser:
            import webbrowser
            webbrowser.open(f"http://localhost:{port}")
        sys.exit(0)


def open_browser_when_ready(port: int) -> None:
    def wait_and_open():
        import webbrowser
        for _ in range(240):
            with socket.socket() as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.5)
        else:
            return
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass
    threading.Thread(target=wait_and_open, daemon=True).start()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8501)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--make-offline-bundle", action="store_true")
    args = ap.parse_args()

    check_python()
    check_folder()

    if args.make_offline_bundle:
        WHEELS.mkdir(exist_ok=True)
        rc, tail = run_logged([sys.executable, "-m", "pip", "download", "-r", str(ROOT / "requirements.txt"), "-d", str(WHEELS)])
        if rc != 0:
            die("The packages could not be downloaded.", *(pip_hint(tail) or ["Check the internet connection and run again."]))
        say(f"packages saved in {WHEELS} - copy the whole folder to the other computer")
        return

    find_licence()                                       # before the long installation, so a missing file shows at once
    ensure_environment(sys.argv[1:])
    already_running(args.no_browser)
    ensure_licence()
    ensure_model(args.rebuild)
    from lipoma_proto import licence
    try:
        n = licence.extract_plain()
    except OSError as exc:
        die(f"The sample images could not be written ({exc}).", "Close programs that use the project folder and run again.")
    say(f"sample images: {licence.IMAGES_DIR.relative_to(ROOT)} ({n} files, removed when the platform stops)")
    guard_plain_images(licence.remove_plain)
    port = pick_port(args.port)
    try:
        RUNNING.write_text(f"{os.getpid()} {port}")
    except OSError:
        pass
    say(f"starting the app on http://localhost:{port}  (press Ctrl+C to stop)")
    if not args.no_browser:
        open_browser_when_ready(port)
    cmd = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"), "--server.port", str(port),
           "--browser.gatherUsageStats", "false", "--server.headless", "true"]
    rc = 0
    try:
        rc = subprocess.call(cmd, cwd=ROOT)
    except KeyboardInterrupt:
        pass
    finally:
        licence.remove_plain()
        try:
            RUNNING.unlink()
        except OSError:
            pass
        say("stopped")
    if rc not in (0, None) and rc > 0 and rc != 130:
        die(f"The app stopped with an error (code {rc}).", "Run again; if it repeats, send the file below to the developer.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[run] stopped", flush=True)
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:                              # anything unexpected: readable message, details in the log
        import traceback
        log("\n" + traceback.format_exc())
        die(f"Unexpected problem: {type(exc).__name__}: {str(exc)[:200]}", "Run again; if it repeats, send the file below to the developer.")
