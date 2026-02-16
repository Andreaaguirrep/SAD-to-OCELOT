# SAD to OCELOT Converter

A simple Python GUI tool to convert **SAD (.sad) lattice files** into **OCELOT-compatible Python lattices**.

## Features

- Parses SAD element definitions
- Supports LINE definitions
- Converts units (DEG → radians)
- Maps common elements (DRIFT, QUAD, BEND, CAVI, etc.)
- Generates ready-to-use OCELOT Python file
- Simple Tkinter GUI

## Requirements

- Python 3.8+
- numpy
- OCELOT
- tkinter (usually included with Python)

## Usage

Run:

```bash
python sad_to_ocelot_gui.py
```

Then:

1. Select input `.sad` file  
2. Choose output `.py` file  
3. Click **Convert**



## Notes

- Unrecognized elements are reported in the GUI

---

Author: I. Agapov, A. Aguirre
