# 6. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `python` is not recognised (Windows) | Python is not on the PATH. Re-run the Python installer and tick **Add python.exe to PATH**, or use `py run.py`. |
| `python3` / `python` not found (macOS, Linux) | Install Python (see [Installation](01-installation.md)) and use `python3 run.py`. |
| "Python 3.10 or newer is required" | Install a newer Python from <https://www.python.org/downloads/>. |
| `No module named venv` (Linux) | `sudo apt install python3-venv`. |
| Package installation fails or stalls | Check the internet connection and run `python run.py` again; it resumes. For a computer without internet use the offline bundle ([Installation](01-installation.md), section 1.5). |
| Not enough disk space during installation | The packages need about 3 GB free. Free some space and run again. |
| "The trained model is missing" | Start with `python run.py`, not `streamlit run app.py` directly; the launcher builds the model. |
| "saved model cannot be loaded here ... it will be rebuilt" | The model was saved with another scikit-learn version. This is normal after moving between computers; the launcher retrains it automatically. |
| Port already in use | `python run.py --port 9000`. |
| The browser does not open | Open <http://localhost:8501> manually, or use the port you chose. |
| The start-up screen stays at a low percentage | The first start loads PyTorch and warms the model and can take up to a minute on a slow computer. If it stops with an error message, run `python run.py --rebuild`. |
| A DICOM file does not open | Install `pydicom` (it is in `requirements.txt`) and check that the file contains pixel data. |
| "Could not open this file" | The file is damaged or not an image. Try PNG or JPG. |
| Changes in `lipoma_proto/` are not visible | Streamlit keeps imported modules in memory. Stop the platform (Ctrl+C) and start it again. |

`python run.py` does the whole set-up by itself (finds the licence file, creates `.venv`, installs the packages with retries, downloads the model weights, trains the model, opens the browser). When it cannot continue it stops with a boxed message that says what went wrong and what to do; run it again afterwards and it continues where it stopped. Messages it can show: Python missing/too old/32-bit, the project run from inside a zip file, an incomplete download, a read-only folder, not enough disk space, no licence file, a blocked internet connection, a broken `.venv` (it is recreated automatically). A second `python run.py` while the platform is running just opens the running one; a busy port is replaced by the next free one.

Everything it does is written to `outputs/setup_log.txt`. If a problem remains, send that file to the developer.
