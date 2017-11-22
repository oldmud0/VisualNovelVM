import pygame
import threading
import struct
from spritesurface import SpriteSurface

MAX_BANKS = 32
MAX_REGISTERS = 8

REGINT = 0
REGSTR = 1
LITINT = 2
LITSTR = 3


class Runtime:
    def __init__(self, window: pygame.Surface, code: bytes):
        self.window = window
        self.code = code
        self.sprite_bank = [None] * MAX_BANKS
        self.threads = []

    def start(self):
        """Start the VM."""
        if len(self.threads) > 0:
            raise RuntimeError("Runtime is already running")
        thread = VMThread(self)
        thread.start()
        self.threads.append(thread)

    def _call_fork(self, pc):
        thread = VMThread(self, pc=pc)
        thread.start()
        self.threads.append(thread)

    def reset(self):
        """Reset state, unload all sprite banks,
        and stop all threads."""
        for thread in self.threads:
            thread.stop()
        self.threads.clear()


class VMThread(threading.Thread):

    def __init__(self, global_state, pc=0):
        threading.Thread.__init__(self)
        self.global_state = global_state
        self.sprite_bank = global_state.sprite_bank
        self.code = global_state.code
        self.pc = pc
        self.str_stack = []
        self.int_stack = []
        self.call_stack = []
        self.regints = [0] * MAX_REGISTERS
        self.regstrs = [""] * MAX_REGISTERS
        self.attr_list = dict()
        self.comparator = 0
        self.running = True

    def run(self):
        while self.running:
            newpc = self.pc
            op = self.opcodes[self.code[self.pc]]
            if op is not None:
                args = []
                for operand in op.operands:
                    if operand == REGINT:
                        newpc += 1
                        args.append(self.code[newpc])
                    elif operand == REGSTR:
                        newpc += 1
                        args.append(self.code[newpc])
                    elif operand == LITINT:
                        newpc += 4
                        args.append(struct.unpack("I", self.code[newpc-3:newpc+1])[0])
                    elif operand == LITSTR:
                        new_str = bytearray()
                        # Buffer overrun problem - but I'll let it happen.
                        while self.code[newpc] != 0x0:
                            new_str.append(self.code[newpc])
                            newpc += 1
                        args.append(new_str.decode("utf-8"))
                # print(f"{self.pc}: {op.__name__}({args})")
                self.pc = newpc
                op.__call__(self, *args)
            else:
                print("Opcode {0} not found".format(self.code[self.pc]))
            self.pc += 1

    def stop(self):
        self.running = False

    def reset(self):
        """Reset state, unload all sprite banks,
        and stop all threads."""
        self.global_state.reset()
    reset.operands = []

    def loadspr(self, regstr_vpath: int, regint_banknum: int):
        """Load a sprite located in a virtual path into a bank."""
        vpath = self.regstrs[regstr_vpath]
        banknum = self.regints[regint_banknum]
        self.sprite_bank[banknum] = SpriteSurface(vpath)
    loadspr.operands = [REGSTR, REGINT]

    def unloadspr(self, regint_banknum: int):
        """Unload the sprite in a bank."""
        self.sprite_bank[self.regints[regint_banknum]] = None
    unloadspr.operands = [REGINT]

    def fork(self, litint_procedure: int):
        """Fork the execution state into another procedure such that
        the next point of execution and the specified procedure run in
        parallel.
        """
        # Final check: are we actually supposed to be running?
        if self.running:
            self.global_state._call_fork()
    fork.operands = [LITINT]

    def ret(self):
        """Return from a procedure."""
        self.pc = self.call_stack.pop()
    ret.operands = []

    def call(self, litint_procedure: int):
        """Call a specified procedure."""
        self.call_stack.append(self.pc)
        self.pc = litint_procedure - 1
    call.operands = [LITINT]

    def pushs(self, regstr: int):
        """Push a string register into the string stack."""
        self.str_stack.append(self.regstrs[regstr])
    pushs.operands = [REGSTR]

    def pops(self, regstr: int):
        """Pop a string from the string stack into a string register."""
        self.regstrs[regstr] = self.str_stack.pop()
    pops.operands = [REGSTR]

    def pushi(self, regint: int):
        """Push an integer register into the integer stack."""
        self.int_stack.append(self.regints[regint])
    pushi.operands = [REGINT]

    def popi(self, regint: int):
        """Pop an integer into a string register."""
        self.regints[regint] = self.int_stack.pop()
    popi.operands = [REGINT]

    def waitms(self, regint_millsecs: int):
        """Delay this execution thread by a given number of milliseconds."""
        pass
    waitms.operands = [REGINT]
    waitms.asm_name = "wait"

    def waithook(self, litstr_hookname: str):
        """Halt this execution thread until the specified hook is fired.
        If there are no other running threads, this call will be canceled
        to prevent hanging."""
        pass
    waithook.operands = [LITSTR]
    waithook.asm_name = "wait"

    def fire(self, litstr_hookname: str):
        """Fire a hook."""
        pass
    fire.operands = [LITSTR]

    def say(self, regint_char_banknum: int, regstr_message: int):
        """Call a 'say' procedure for the given character."""
        pass
    say.operands = [REGINT, REGSTR]

    def setls(self, regstr: int, litstr: str):
        """Set a string register to a literal value."""
        self.regstrs[regstr] = litstr
    setls.operands = [REGSTR, LITSTR]
    setls.asm_name = "set"

    def setli(self, regint: int, litint: int):
        """Set an integer register to a literal value."""
        self.regints[regint] = litint
    setli.operands = [REGINT, LITINT]
    setli.asm_name = "set"

    def setrs(self, regstr1: int, regstr2: int):
        """Set string register 1 to string register 2."""
        self.regstrs[regstr1] = self.regstrs[regstr2]
    setrs.operands = [REGSTR, REGSTR]
    setrs.asm_name = "set"

    def setri(self, regint1: int, regint2: int):
        """Set integer register 1 to integer register 2."""
        self.regints[regint1] = self.regints[regint2]
    setri.operands = [REGINT, REGINT]
    setri.asm_name = "set"

    def show(self, regint_banknum: int, regint_alpha):
        """Set the alpha of a sprite.
        Attributes: 'fade' (any int >= 0) """
        self.sprite_bank[self.regints[regint_banknum]].alpha = self.regints[regint_alpha]
    show.operands = [REGINT, REGINT]

    def layer(self, regint_banknum: int, regint_layer):
        """Set the z-order/layer number of a sprite.
        Higher is more priority."""
        pass
    layer.operands = [REGINT, REGINT]

    def attri(self, litstr_attribute_name: str, regint_attribute_value: int):
        """Append an attribute/modifier to the next applicable operation
        with an integer value."""
        self.attr_list[litstr_attribute_name] = self.regints[regint_attribute_value]
    attri.operands = [LITSTR, REGINT]
    attri.asm_name = "attr"

    def attrs(self, litstr_attribute_name: str, regstr_attribute_value: int):
        """Append an attribute/modifier to the next applicable operation
        with a string value."""
        self.attr_list[litstr_attribute_name] = self.regstrs[regstr_attribute_value]
    attrs.operands = [LITSTR, REGSTR]
    attrs.asm_name = "attr"

    def openbank(self, regint_banknum: int):
        """Return the number of an open bank slot into a specified register."""
        for index, bank in enumerate(self.sprite_bank):
            if bank is None:
                self.regints[regint_banknum] = index
                return
    openbank.operands = [REGINT]

    def addr(self, regint1: int, regint2: int):
        """Add regint2 to regint1."""
        self.regints[regint1] += self.regints[regint2]
    addr.operands = [REGINT, REGINT]
    addr.asm_name = "add"

    def subr(self, regint1: int, regint2: int):
        """Subtract regint2 from regint1."""
        self.regints[regint1] += self.regints[regint2]
    subr.operands = [REGINT, REGINT]
    subr.asm_name = "sub"

    def concatl(self, regstr: int, litstr: str):
        """Concatenate literal string to string register."""
        self.regstrs[regstr] += litstr
    concatl.operands = [REGSTR, LITSTR]
    concatl.asm_name = "concat"

    def concatr(self, regstr1: int, regstr2: int):
        """Concatenate regstr2 to regstr1."""
        self.regstrs[regstr1] += self.regstrs[regstr2]
    concatr.operands = [REGSTR, REGSTR]
    concatr.asm_name = "concat"

    def cmp_iil(self, regint: int, litint: int):
        """Compare an integer register to a literal integer numerically."""
        self.comparator = self.regints[regint] - litint
    cmp_iil.operands = [REGINT, LITINT]
    cmp_iil.asm_name = "cmp"

    def cmp_iir(self, regint1: int, regint2: int):
        """Compare regint1 to regint2 numerically."""
        self.comparator = self.regints[regint1] - self.regints[regint2]
    cmp_iir.operands = [REGINT, REGINT]
    cmp_iir.asm_name = "cmp"

    def jl(self, litint: int):
        """Jump to procedure if comparison is less than 0."""
        if self.comparator < 0:
            self.pc = litint - 1
    jl.operands = [LITINT]

    def je(self, litint: int):
        """Jump to procedure if comparison is equal to 0."""
        if self.comparator == 0:
            self.pc = litint - 1
    je.operands = [LITINT]

    def jg(self, litint: int):
        """Jump to procedure if comparison is greater than 0."""
        if self.comparator > 0:
            self.pc = litint - 1
    jg.operands = [LITINT]

    def jmp(self, litint: int):
        """Jump to procedure."""
        self.pc = litint - 1
    jmp.operands = [LITINT]

    @staticmethod
    def op_name(op):
        try:
            return op.asm_name
        except AttributeError:
            return op.__name__

    opcodes = {
        0x00: reset,
        0x01: loadspr,
        0x02: unloadspr,
        0x03: fork,
        0x04: ret,
        0x05: call,
        0x06: pushs,
        0x07: pops,
        0x08: pushi,
        0x09: popi,
        0x0a: waitms,
        0x0b: waithook,
        0x0c: fire,
        0x0d: say,
        0x0e: setls,
        0x0f: setli,
        0x10: setrs,
        0x11: setri,
        0x12: show,
        0x13: layer,
        0x14: attri,
        0x15: attrs,
        0x16: openbank,
        0x17: addr,
        0x18: subr,
        0x19: concatl,
        0x1a: concatr,
        0x1b: cmp_iil,
        0x1c: cmp_iir,
        0x1d: jl,
        0x1e: je,
        0x1f: jg,
        0x20: jmp,
    }
