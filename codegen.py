import argparse
import re
from vm import VMThread

parser = argparse.ArgumentParser(description="Assemble a VNVM binary.")
parser.add_argument("file", type=str, nargs="1", help="the file to be assembled")
parser.add_argument("-v", "--verbose", action="count", help="make it complain more")

args = parser.parse_args()

opcodes = dict()
for opval, opfunc in enumerate(VMThread.opcodes):
    name = opfunc.asm_name or opfunc.__name__
    if opcodes[name] is None:
        opcodes[name] = []
    opcodes[name].append((opval, opfunc))

with open(args.file) as file:
    for line in file.readlines():
        if args.verbosity == 2: print(line)
        line.strip()
        # Strip comments
        re.sub("\s*;.*+$", "", line, flags=re.MULTILINE)
