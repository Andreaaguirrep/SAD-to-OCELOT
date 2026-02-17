import argparse
import re
from typing import NamedTuple
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

# --- Parsing ---
class LatticeObject:
    def __init__(self):
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

                # Detect negative operator FIRST
                if token_stack[-1].type == "OP" and token_stack[-1].value == "-":
                    token_stack.pop()  # remove '-'

                    # Next token must be ID (negative element)
                    if len(token_stack) > 0 and token_stack[-1].type == "ID":
                        neg_id = token_stack.pop()
                        # print(f"⚠️ Warning: Negative element detected in LINE: -{neg_id.value}")
                        line_def.append(neg_id.value)
                    continue

                # Normal element
                if token_stack[-1].type == "ID":
                    t1 = token_stack.pop()
                    line_def.append(t1.value)

                else:
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
    def __init__(self, fname, debug=False):
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

        skip_mode = False
        known_elements = {'DRIFT', 'QUAD', 'BEND', 'SBEND', 'SEXT', 'OCT', 'MONI', 'MULT', 'SOL', 'CAVI', 'MARK', 'APERT', 'MAP','COORD'}

        for line in text.splitlines():
            if 'MOMENTUM' in line.upper():
                skip_mode = True
                continue
            if skip_mode:
                if any(element in line.upper() for element in known_elements):
                    skip_mode = False
                else:
                    continue
            for token in tokenize(line + '\n'):
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

# --- Converter ---
def convert_sad_to_ocelot(input_file, output_file):
    sad_obj = read_sad(input_file, debug=False)
    unrecognized = []

    with open(output_file, "w") as f:
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
                print(f"⚠️ Warning: MULT element detected and simplified to Quadrupole/Drift: {o.name}")
                if o.get_parameter('L') > 0:
                    k1 = o.get_parameter('K1') / o.get_parameter('L')
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

    print(f"\n✅ Conversion complete! Output saved to: {output_file}")
    if unrecognized:
        print("\n⚠️ Unrecognized element types found:")
        for item in unrecognized:
            print(f" - {item}")

# --- CLI Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert SAD file to OCELOT format")
    parser.add_argument("input", help="Path to the input SAD file")
    parser.add_argument("-o", "--output", help="Output Python file (default: same name as input with .py extension)")
    args = parser.parse_args()

    # If no output specified, use input filename with .py extension
    if args.output:
        output_file = args.output
    else:
        if args.input.lower().endswith(".sad"):
            output_file = args.input[:-4] + ".py"
        else:
            output_file = args.input + ".py"

    convert_sad_to_ocelot(args.input, output_file)
