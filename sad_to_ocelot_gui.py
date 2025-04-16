import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from typing import NamedTuple
import re
from numpy import pi

# --- Tokenizer ---
class Token(NamedTuple):
    type: str
    value: str
    line: int
    column: int

def tokenize(code):
    keywords = ['QUAD', 'MARK', 'CAVI', 'BEAMBEAM', 'APERT', 'SOL', 'DRIFT', 'BEND',
                'SEXT', 'OCT', 'MULT', 'MONI', 'LINE', 'MAP', 'COORD', 'APERT']
    token_specification = [
        ('NUMBER',   r'([+-])?\d+(\.\d*)?(e[-+]?\d+)?|([+-])?\d*(\.\d+)(e[-+]?\d+)?'),
        ('ASSIGN',   r':='),
        ('EQUAL',    r'='),
        ('END',      r';'),
        ('COMMENT',  r'!.*'),
        ('LBR',      r'\('),
        ('RBR',      r'\)'),
        ('UNIT',     r'DEG'),
        ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'),
        ('OP',       r'[+\-*/]'),
        ('NEWLINE',  r'\n'),
        ('SKIP',     r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    line_num = 1
    line_start = 0
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start
        if kind == 'NUMBER':
            value = float(value)
        elif kind == 'ID' and value in keywords:
            kind = "ELEMENT_TYPE"
        elif kind == 'NEWLINE':
            line_start = mo.end()
            line_num += 1
            continue
        elif kind == 'SKIP' or kind == 'COMMENT':
            continue
        elif kind == 'MISMATCH':
            raise RuntimeError(f'{value!r} unexpected on line {line_num}')
        yield Token(kind, value, line_num, column)

# --- Parsing classes ---
class LatticeObject:
    def __init__(self) -> None:
        self.type = "None"
        self.name = None
        self.parameters = {}

    def get_parameter(self, name):
        return self.parameters.get(name, 0.0)

    def __str__(self):
        return f"{self.type} : {self.name}  :  {self.parameters}"

def process_stack(token_stack):
    lattice_objects = []
    line_def = []
    in_element_def = False
    in_line = False
    element_name = None
    element_type = None

    while len(token_stack) > 0:
        if len(token_stack) >= 1 and token_stack[-1].type == 'ELEMENT_TYPE':
            t1 = token_stack.pop()
            element_type = t1.value
            if element_type == 'LINE':
                in_line = True

        if not in_element_def:
            if len(token_stack) >= 3 and token_stack[-1].type == "ID" and token_stack[-2].type == "EQUAL" and token_stack[-3].type == "LBR":
                in_element_def = True
                t1 = token_stack.pop()
                token_stack.pop()
                token_stack.pop()
                element_name = t1.value
                e = LatticeObject()
                e.type = element_type
                e.name = element_name
                if not in_line:
                    lattice_objects.append(e)
            else:
                token_stack.pop()
                continue

        if in_element_def and len(token_stack) > 0:
            if token_stack[-1].type == "RBR":
                token_stack.pop()
                in_element_def = False

            elif in_line:
                if token_stack[-1].type == "ID":
                    t1 = token_stack.pop()
                    line_def.append(t1.value)
                elif token_stack[-1].type == "OP":
                    token_stack.pop()
                    token_stack.pop()

            elif len(token_stack) >= 3 and token_stack[-1].type == "ID" and token_stack[-2].type == "EQUAL" and token_stack[-3].type == "NUMBER":
                t1 = token_stack.pop()
                token_stack.pop()
                t3 = token_stack.pop()
                lattice_objects[-1].parameters[t1.value] = t3.value
                if len(token_stack) > 0 and token_stack[-1].type == "UNIT" and token_stack[-1].value == "DEG":
                    lattice_objects[-1].parameters[t1.value] = t3.value * pi / 180.
                    token_stack.pop()

        if len(token_stack) > 0 and token_stack[-1].type == "END":
            token_stack.pop()

    return lattice_objects, line_def

class SADObject:
    def __init__(self, fname, debug=False) -> None:
        self.lattice_objects = {}
        self.lattice_list = []
        self.fname = fname
        self.debug = debug
        self.parse()

    def parse(self):
        try:
            with open(self.fname, "r") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"File {self.fname} not found.")
            return

        token_stack = []
        object_defs = []
        object_dict = {}
        line_def = []

        skip_mode = False  # Start with full parsing
        known_elements = {'DRIFT', 'QUAD', 'BEND', 'SBEND', 'SEXT', 'OCT', 'MONI', 'MULT', 'SOL', 'CAVI', 'MARK', 'APERT', 'MAP','COORD'}

        for line in text.splitlines():
            if 'MOMENTUM' in line.upper():
                skip_mode = True
                continue

            if skip_mode:
                # Check if any known element type is in the line to resume parsing
                if any(element in line.upper() for element in known_elements):
                    skip_mode = False
                else:
                    continue  # Keep skipping

            for token in tokenize(line + '\n'):  # add newline to keep tokenizer happy
                token_stack = [token] + token_stack
                if token.type == "END":
                    objs, line_def = process_stack(token_stack)
                    token_stack.clear()

                    for o in objs:
                        object_defs.append(o)
                        object_dict[o.name] = o

        self.lattice_objects = object_defs
        self.object_dict = object_dict
        self.lattice_list = line_def


def read_sad(fname, debug=False):
    return SADObject(fname, debug)

# --- GUI Class ---
class SADtoOCELOTGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SAD to OCELOT Converter")

        self.sad_file = None
        self.output_file = "OcelotOutput.py"

        tk.Label(root, text="Select SAD file to convert:").pack(pady=5)
        tk.Button(root, text="Choose Input File", command=self.choose_file).pack()

        tk.Button(root, text="Select Output File", command=self.select_output_file).pack(pady=5)

        self.convert_button = tk.Button(root, text="Convert to OCELOT", command=self.convert_file, state=tk.DISABLED)
        self.convert_button.pack(pady=5)

        self.text_area = scrolledtext.ScrolledText(root, height=20, width=80)
        self.text_area.pack(padx=10, pady=10)

    def choose_file(self):
        self.sad_file = filedialog.askopenfilename(filetypes=[("SAD files", "*.sad")])
        if self.sad_file:
            self.text_area.insert(tk.END, f"Selected input file: {self.sad_file}\n")
            self.convert_button.config(state=tk.NORMAL)

    def select_output_file(self):
        self.output_file = filedialog.asksaveasfilename(defaultextension=".py",
                                                        filetypes=[("Python Files", "*.py")],
                                                        initialfile="PRUEBA.py")
        if self.output_file:
            self.text_area.insert(tk.END, f"Selected output file: {self.output_file}\n")

    def convert_file(self):
        if not self.sad_file:
            messagebox.showerror("Error", "No input file selected.")
            return

        self.text_area.insert(tk.END, f"\nConverting {self.sad_file}...\n")
        sad_obj = read_sad(self.sad_file, debug=False)

        try:
            unrecognized = []

            with open(self.output_file, "w") as f:
                f.write("# Converted from a SAD FILE\n")
                f.write("from ocelot.cpbd.elements import *\n#elements\n")
                for o in sad_obj.lattice_objects:
                    if o.type == "DRIFT":
                        f.write(f"{o.name} = Drift(eid=\"{o.name}\",l={o.get_parameter('L')})\n")
                    elif o.type == "MONI":
                        f.write(f"{o.name} = Monitor(eid=\"{o.name}\",l={o.get_parameter('L')})\n")
                    elif o.type in ["MARK", "MAP", "APERT", "COORD"]:
                        f.write(f"{o.name} = Marker(eid=\"{o.name}\")\n")
                    elif o.type == "BEND":
                        e1 = o.get_parameter('E1') * o.get_parameter('ANGLE')
                        e2 = o.get_parameter('E2') * o.get_parameter('ANGLE')
                        tilt = o.get_parameter('ROTATE')
                        f.write(f"{o.name} = SBend(eid=\"{o.name}\",l={o.get_parameter('L')},angle={o.get_parameter('ANGLE')},e1={e1},e2={e2},tilt={-tilt})\n")
                    elif o.type == "QUAD":
                        k1 = o.get_parameter('K1') / o.get_parameter('L') if o.get_parameter('L') else 0.0
                        f.write(f"{o.name} = Quadrupole(eid=\"{o.name}\",l={o.get_parameter('L')},k1={k1},tilt={o.get_parameter('ROTATE')})\n")
                    elif o.type == "SEXT":
                        f.write(f"{o.name} = Sextupole(eid=\"{o.name}\",l={o.get_parameter('L')},k2={o.get_parameter('K2')},tilt={o.get_parameter('ROTATE')})\n")
                    elif o.type == "MULT":
                        if o.get_parameter('L') > 0:
                            k1 = o.get_parameter('K1') / o.get_parameter('L') if o.get_parameter('L') else 0.0
                            f.write(f"{o.name} = Quadrupole(eid=\"{o.name}\",l={o.get_parameter('L')},k1={k1},tilt={o.get_parameter('ROTATE')})\n")
                        else:
                            f.write(f"{o.name} = Drift(eid=\"{o.name}\",l={o.get_parameter('L')})\n")
                    elif o.type == "SOL":
                        f.write(f"{o.name} = Solenoid(eid=\"{o.name}\",l={o.get_parameter('L')})\n")
                    elif o.type == "CAVI":
                        phi = 90 + o.get_parameter('PHI') * 180 / pi
                        f.write(f"{o.name} = Cavity(eid=\"{o.name}\",l={o.get_parameter('L')},freq={o.get_parameter('FREQ')}, v={o.get_parameter('VOLT')*1.e-9}, phi={phi})\n")
                    else:
                        f.write(f"# Unrecognized type {o}\n")
                        unrecognized.append(f"{o.type} ({o.name})")

                f.write("END = Marker()\n")
                f.write("#lattice def\nlattice_list = (")
                for e in sad_obj.lattice_list:
                    f.write(f"{e}, ")
                f.write("END)\n")

            self.text_area.insert(tk.END, f"✅ Conversion complete! Output saved to:\n{self.output_file}\n")
            if unrecognized:
                self.text_area.insert(tk.END, "\n⚠️ Unrecognized element types found:\n")
                for item in unrecognized:
                    self.text_area.insert(tk.END, f" - {item}\n")

        except Exception as e:
            self.text_area.insert(tk.END, f"❌ Error during conversion: {e}\n")

# --- Launch GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    app = SADtoOCELOTGUI(root)
    root.mainloop()

