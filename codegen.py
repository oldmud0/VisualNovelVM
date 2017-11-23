import argparse
import struct
import shlex
import vm
from vm import VMThread


class AssemblyError(Exception):
    def __init__(self, line_no, message):
        super().__init__(f"line {line_no}: {message}")


parser = argparse.ArgumentParser(description="Assemble a VNVM binary.")
parser.add_argument("input", type=str, nargs=1, help="the file to be assembled")
parser.add_argument("output", type=str, nargs=1, help="the file to output to")
parser.add_argument("-v", "--verbose", action="count", help="make it complain more",
                    default=0)

args = parser.parse_args()

opcodes = dict()
for opval, opfunc in VMThread.opcodes.items():
    try:
        name = opfunc.asm_name
    except AttributeError:
        name = opfunc.__name__
    if name not in opcodes:
        opcodes[name] = []
    opcodes[name].append((opval, opfunc))

if args.verbose == 1: print(f"opening {args.input}")
with open(args.input[0]) as file:
    output = bytearray()
    lines = file.readlines()

    # Scan for procedure labels
    procedures = dict()
    procedure_refs = []

    if args.verbose >= 1:
        print(f"assembling {len(lines)} lines")

    # Scan for opcodes
    for line_no, line in enumerate(lines):
        if args.verbose >= 2:
            print(f"{line_no}/{len(output)}: {line.strip()}")
        line.strip()
        tokens = list(shlex.split(line, comments=True))

        # Strip semicolon comments
        try:
            tokens = tokens[:tokens.index(';')]
        except ValueError:
            pass

        if len(tokens) > 0:
            # Procedure label
            if len(tokens) == 1 and tokens[0][-1] == ':':
                procedure_name = tokens[0][:-1]
                if args.verbose >= 2:
                    print(f"{line_no}: procedure {procedure_name} @ {len(output)}")
                if procedure_name not in procedures:
                    procedures[procedure_name] = len(output)
                else:
                    raise AssemblyError(line_no, f"duplicate procedure {procedure_name}")
                continue

            opname = tokens[0]
            if opname not in opcodes:
                raise AssemblyError(line_no, f"invalid opcode {tokens[0]}")

            # Assemble operand by operand
            # Try each interpretation of the opcode, though
            error = None
            for interpretation in opcodes[opname]:
                if args.verbose >= 2:
                    print(f"{line_no}: interpreting as {interpretation[1].__name__}")

                buffer = bytearray()

                # Write the operation
                buffer.append(interpretation[0])

                try:
                    operands = interpretation[1].operands
                    for token, operand_type in zip(tokens[1:], operands):
                        if operand_type == vm.REGINT:
                            if not token[1:].isnumeric() or not token[0] == 'i':
                                raise AssemblyError(line_no, f"{token} is not a register")
                            buffer.append(int(token[1:]))
                        elif operand_type == vm.LITINT:
                            try:
                                token_int = int(token)
                                buffer.extend(struct.pack("i", token_int))
                            except ValueError:
                                if token[0] == '@':
                                    procedure_refs.append((len(output) + len(buffer), token[1:]))
                                    buffer.extend(struct.pack("I", 0))
                                else:
                                    raise AssemblyError(line_no, f"{token} is not a number or procedure")
                        elif operand_type == vm.REGSTR:
                            if not token[1:].isnumeric() or not token[0] == 's':
                                raise AssemblyError(line_no, f"{token} is not a register")
                            buffer.append(int(token[1:]))
                        elif operand_type == vm.LITSTR:
                            buffer.extend(token.encode("utf-8"))
                            buffer.append(0)
                    # Break if there is no error
                    output.extend(buffer)
                    error = None
                    break
                except AssemblyError as e:
                    error = e
            if error:
                raise error

    if args.verbose >= 1:
        print("committing procedure table")

    # Replace the procedure references with the actual addresses
    for procedure_ref in procedure_refs:
        location, name = procedure_ref
        if name in procedures:
            # Sorry, we're going to have to mutate the output
            # to get the integer in
            output = output[:location]\
                     + struct.pack("I", procedures[name])\
                     + output[location+4:]
        else:
            raise AssemblyError(0, f"procedure {name} not found")

    if args.verbose >= 1:
        print(f"writing to {args.output}")

    with open(args.output[0], "wb") as output_file:
        output_file.write(output)

    if args.verbose >= 1:
        print("Finished")