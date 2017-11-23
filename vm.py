import pygame
import threading
import struct
from spritesurface import SpriteSurface

MAX_BANKS = 32

LITINT = 0
LITSTR = 1


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
        self.attr_list = dict()
        self.running = True

    def run(self):
        while self.running:
            newpc = self.pc
            op = self.opcodes[self.code[self.pc]]
            if op is not None:
                args = []
                for operand in op.operands:
                    if operand == LITINT:
                        newpc += 4
                        args.append(struct.unpack("I", self.code[newpc-3:newpc+1])[0])
                    elif operand == LITSTR:
                        newpc += 1
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
        self.running = False
        self.global_state.reset()
    reset.operands = []

    def loadspr(self):
        """Load a sprite located in a virtual path into a bank."""
        vpath = self.int_stack.pop()
        banknum = self.int_stack.pop()
        self.sprite_bank[banknum] = SpriteSurface(vpath)
    loadspr.operands = []

    def unloadspr(self):
        """Unload the sprite in a bank."""
        self.sprite_bank[self.int_stack.pop()] = None
    unloadspr.operands = []

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

    def pushs(self, litstr: str):
        """Push a string register into the string stack."""
        self.str_stack.append(litstr)
    pushs.operands = [LITSTR]

    def pushi(self, litint: int):
        """Push an integer register into the integer stack."""
        self.int_stack.append(litint)
    pushi.operands = [LITINT]

    def waitms(self, litint_ms: int):
        """Delay this execution thread by a given number of milliseconds."""
        pass
    waitms.operands = [LITINT]
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

    def say(self):
        """Call a 'say' procedure for the given character."""
        pass
    say.operands = []

    def show(self):
        """Set the alpha of a sprite.
        Attributes: 'fade' (any int >= 0) """
        self.sprite_bank[self.int_stack.pop()].alpha = self.int_stack.pop()
    show.operands = []

    def layer(self):
        """Set the z-order/layer number of a sprite.
        Higher is more priority."""
        pass
    layer.operands = []

    def attri(self):
        """Append an attribute/modifier to the next applicable operation
        with an integer value."""
        self.attr_list[self.str_stack.pop()] = self.int_stack.pop()
    attri.operands = []

    def attrs(self):
        """Append an attribute/modifier to the next applicable operation
        with a string value."""
        self.attr_list[self.str_stack.pop()] = self.str_stack.pop()
    attrs.operands = []

    def openbank(self):
        """Return the number of an open bank slot."""
        for index, bank in enumerate(self.sprite_bank):
            if bank is None:
                self.int_stack.append(index)
                return
    openbank.operands = []

    def concat(self):
        """Concatenate two strings."""
        self.str_stack.append(self.str_stack.pop(-2) + self.str_stack.pop())
    concat.operands = []

    def jl(self, litint: int):
        """Jump to procedure if top is less than 0."""
        if self.int_stack.pop() < 0:
            self.pc = litint - 1
    jl.operands = [LITINT]

    def je(self, litint: int):
        """Jump to procedure if top is equal to 0."""
        if self.int_stack.pop() == 0:
            self.pc = litint - 1
    je.operands = [LITINT]

    def jg(self, litint: int):
        """Jump to procedure if top is greater than 0."""
        if self.int_stack.pop() > 0:
            self.pc = litint - 1
    jg.operands = [LITINT]

    def jmp(self, litint: int):
        """Jump to procedure."""
        self.pc = litint - 1
    jmp.operands = [LITINT]

    def castis(self):
        """Cast an integer into a string."""
        self.str_stack = str(self.int_stack.pop())
    castis.operands = []
    castis.asm_name = "cast"

    def dbgs(self):
        """Debug print a string."""
        print(self.str_stack[-1])
    dbgs.operands = []
    dbgs.asm_name = "dbgs"

    def dbgi(self):
        """Debug print an integer."""
        print(self.int_stack[-1])
    dbgi.operands = []
    dbgi.asm_name = "dbgi"

    def add(self):
        self.int_stack.append(self.int_stack.pop() + self.int_stack.pop())
    add.operands = []
    add.asm_name = "add"

    def sub(self):
        self.int_stack.append(self.int_stack.pop(-2) - self.int_stack.pop())
    sub.operands = []
    sub.asm_name = "sub"

    def mul(self):
        self.int_stack.append(self.int_stack.pop() * self.int_stack.pop())
    mul.operands = []
    mul.asm_name = "mul"

    def div(self):
        self.int_stack.append(int(self.int_stack.pop(-2) / self.int_stack.pop()))
    div.operands = []
    div.asm_name = "div"

    def dups(self):
        """Duplicate the top of the string stack."""
        self.str_stack.append(self.str_stack[-1])
    dups.operands = []

    def dupi(self):
        """Duplicate the top of the integer stack."""
        self.int_stack.append(self.int_stack[-1])
    dupi.operands = []

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
        0x08: pushi,
        0x0a: waitms,
        0x0b: waithook,
        0x0c: fire,
        0x0d: say,
        0x12: show,
        0x13: layer,
        0x14: attri,
        0x15: attrs,
        0x16: openbank,
        0x19: concat,
        0x1d: jl,
        0x1e: je,
        0x1f: jg,
        0x20: jmp,
        0x21: castis,
        0x22: dbgs,
        0x23: dbgi,
        0x24: add,
        0x25: sub,
        0x26: mul,
        0x27: div,
        0x28: dups,
        0x28: dupi,
    }
