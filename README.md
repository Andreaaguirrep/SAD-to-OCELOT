# SAD to OCELOT Converter

Python script to convert **SAD lattice files** into **OCELOT-compatible Python lattices**.

This tool parses accelerator lattice definitions written in **SAD (Strategic Accelerator Design)** format and generates a Python file that can be used directly with the **OCELOT** beam dynamics framework.

---

## Features

- Token-based SAD parser
- Converts common lattice elements to OCELOT objects
- Automatically generates output filename from input
- Detects and warns about:
  - `MULT` elements (simplified during conversion)
- Handles:
  - DRIFT
  - QUAD
  - BEND
  - SEXT
  - SOL
  - CAVI
  - MONI
  - MARK
  - MAP
  - APERT
  - COORD
  - MULT (simplified)

---

## Requirements

- Python 3.8+
- `numpy`
- OCELOT (for using the generated file)

TO INSTALL OCELOT:

```bash
pip install ocelot-collab
```

---

## Usage

Basic usage:

```bash
python sad_to_ocelot.py input_file.sad
```

This automatically generates:

```
input_file.py
```

in the same directory.

---

### Optional Output Filename

You can manually specify the output file:

```bash
python sad_to_ocelot.py input_file.sad -o custom_output.py
```

---

## Element Conversion Overview

| SAD Type | Converted To (OCELOT) |
|----------|-----------------------|
| DRIFT    | `Drift`               |
| QUAD     | `Quadrupole`          |
| BEND     | `SBend`               |
| SEXT     | `Sextupole`           |
| SOL      | `Solenoid`            |
| CAVI     | `Cavity`              |
| MONI     | `Monitor`             |
| MARK     | `Marker`              |
| MAP      | `Marker`              |
| APERT    | `Marker`              |
| COORD    | `Marker`              |
| MULT     | Simplified to `Quadrupole` or `Drift` |

---

## ⚠️ Important Notes

### MULT Elements

`MULT` elements in SAD are currently simplified during conversion:

- If `L > 0` → converted to `Quadrupole`
- If `L == 0` → converted to `Drift`

A warning is printed:

```
⚠️ Warning: MULT element detected and simplified to Quadrupole/Drift: ELEMENT_NAME
```

⚠️ **Important:** During development we discovered that some `MULT` elements in certain SAD lattices may actually represent RF cavity structures or composite elements with additional embedded components.

Because of this, automatic simplification may remove important physics.

If you encounter `MULT` elements in your lattice, please verify their physical meaning before using the converted file for detailed beam dynamics studies. You may contact the repository maintainer for clarification or support.

---

## Authors

 I. Agapov, A. Aguirre

## Support

This work was partially supported by the European Union's Horizon Europe Marie Sklodowska-Curie Staff Exchanges programme under grant agreement no. 101086276. (EAJADE)

For any questions: andrea.aguirre.polo@desy.de


