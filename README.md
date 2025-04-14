# TXWeather Log Parser and Weather Code Assigner

This repository contains a Python toolset designed to parse Telescope Array (TAx4) detector run logs, extract weather information from structured XML files, and generate `.weather.log` files per data segment. Optional plotting features help visualize time coverage and weather code placement.

---

## 📦 Features

- Parses TAx4 run logs and infers missing stop times.
- Matches local and remote weather codes to time segments.
- Applies robust time-weighted averaging (including haze-specific rules).
- Outputs `.weather.log` files with surrounding weather context.
- Optional visualization of time segments and weather entries.

---

## 🔧 Requirements

- Python 3.8+
- `numpy`, `matplotlib`

---

## 🚀 Quickstart

### 1. **Run the Script on a Single File**

```bash
python main.py -d brtax4 path/to/logfile.xml
```

Add `--plot` to visualize the night's data:

```bash
python main.py -d brtax4 path/to/logfile.xml --plot
```

### 2. **Batch Process All Logs (Example)**

```bash
python taweat_run.py
```

(This runs `main.py` over all log files for the detector specified in `taweat_run.py`.)

---

## 📁 Directory Structure

- `main.py` — Entry point that orchestrates parsing, weather assignment, and output writing.
- `taweat_run.py` — Batch execution over a log file directory.
- `parser.py` — Extracts run parts and weather code timestamps from the XML structure.
- `weather.py` — Assigns weather codes using custom logic including pre/post-run handling and interpolation.
- `utils.py` — Time conversion, XML loading, and helper functions.
- `clouds.py` — Weather code interpretation and comparison logic.
- `data_part.py` — Container class for time segments and their associated weather codes.
- `writer.py` — Outputs `.weather.log` files per segment.
- `plotting.py` — Visualizes weather entries and run segments on a timeline.

---

## 🧠 Notes on Logic

- **Pre/post-run codes** are handled specially and optionally prepended/appended.
- **Remote timestamps** are inserted to fill gaps > 1 hour when local-only would be insufficient (specific to `brtax4`).
- **Haze value rules**: When averaging, haze is treated non-linearly (1 = hazy, 2 = uncertain, 0 = clear).

---

## 🗂 Output Format

Each `.weather.log` file contains a line:

```
<start_time>   <prev_code>   <current_code>   <next_code>
```

This format supports time-evolution analysis across the night.

---

## 👤 Author

Zane Gerber  
August 2024

---

## 📜 License

MIT License or your collaboration’s standard license.
