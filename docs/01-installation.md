# 1. Installation

The platform runs on Windows 10/11, macOS 12+ and current Linux distributions. Everything it needs, apart from Python itself, is installed automatically by one command.

## 1.1 Required software

| Software | Version | Needed for | Download |
|---|---|---|---|
| **Python** | 3.10 or newer, 64-bit (tested with 3.14.7 on Windows 11) | running the platform | <https://www.python.org/downloads/> |
| **A web browser** | current Chrome, Edge, Firefox or Safari | viewing the platform | already installed on most computers |
| **Git** (optional) | any | downloading the project with `git clone` | <https://git-scm.com/downloads> |

Platform-specific Python downloads:

- Windows: <https://www.python.org/downloads/windows/>
- macOS: <https://www.python.org/downloads/macos/>
- Linux: use the package manager (for example `sudo apt install python3 python3-venv python3-pip`) or <https://www.python.org/downloads/source/>

Everything else (Streamlit, PyTorch, scikit-learn, pandas, NumPy, Pillow, joblib, pydicom) is listed in [`requirements.txt`](../requirements.txt) and installed automatically into a private `.venv` folder inside the project. Nothing is installed system-wide.

### Installing Python on Windows

1. Open <https://www.python.org/downloads/> and download the latest Python 3 installer for Windows.
2. Run it. **Tick "Add python.exe to PATH"** on the first screen, then choose *Install Now*.
3. Open a new Command Prompt and check: `python --version` (it must show 3.10 or newer).

### Installing Python on macOS

Download the macOS installer from <https://www.python.org/downloads/macos/> and run it, then check with `python3 --version`. Use `python3` instead of `python` in the commands below.

### Installing Python on Linux

```
sudo apt update
sudo apt install python3 python3-venv python3-pip
python3 --version
```

## 1.2 Computer requirements

| Item | Requirement |
|---|---|
| Memory | 4 GB minimum, 8 GB recommended |
| Free disk space | about 4 GB (the Python packages, mainly PyTorch, and the BiomedCLIP model, about 800 MB, are most of it) |
| Processor | any 64-bit CPU; a GPU is not needed |
| Internet | needed once to download the packages and the BiomedCLIP model; afterwards the platform runs offline |

These figures are guidelines for planning.

## 1.3 Get the project

Either download the ZIP from GitHub (**Code > Download ZIP**) and extract it, or clone it:

```
git clone https://github.com/shahulmoonx-star/lipoma-image-analysis.git
cd lipoma-image-analysis
```

Keep the folder structure unchanged. The dataset (`dataset_curated/`) and the network weights (`models/`) must stay inside the project folder.

## 1.4 Start the platform

Open a terminal **inside the project folder** and run:

```
python run.py
```

Windows users can also double-click **`start.bat`**. On macOS and Linux use `python3 run.py`.

What happens on the first run:

1. A private environment is created in `.venv`.
2. The packages in `requirements.txt` are installed (a few minutes, internet needed).
3. The model is trained from `dataset_curated/` (a few minutes) and saved in `artifacts/`.
4. The platform opens at <http://localhost:8501> with a start-up screen that shows the loading percentage.

Later runs skip steps 1 to 3 and start in a few seconds.

### Options

| Command | Effect |
|---|---|
| `python run.py --port 9000` | use another port |
| `python run.py --no-browser` | do not open the browser automatically |
| `python run.py --rebuild` | retrain the model even if one exists |
| `python run.py --make-offline-bundle` | download all packages into `wheels/` so another computer without internet can install them |

To stop the platform press **Ctrl+C** in the terminal.

## 1.5 Computers without internet

On a computer that has internet and the same operating system and Python version:

```
python run.py --make-offline-bundle
```

Copy the whole project folder (including the new `wheels/` folder) to the other computer and run `python run.py`. The launcher detects `wheels/` and installs without internet.
