from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import json
import copy


# Operand class
@dataclass()
class Operand:
    immediate: bool
    name: str
    bytes: int
    value: int | None
    adjust: Literal["+", "-"] | None

    def create(self, value: int):
        return Operand(immediate=self.immediate, name=self.name, bytes=self.bytes, value=value, adjust=self.adjust)

    def setValue(self, value: int):
        self.value = value

    def copy(self):
        return copy.copy(self)

    def print(self):
        if self.adjust is None:
            adjust = ""
        else:
            adjust = self.adjust
        if self.value is not None:
            if self.bytes is not None:
                val = hex(self.value)
            else:
                val = self.value
            v = val
        else:
            v = self.name
        v = v + adjust
        if self.immediate:
            return v
        return f'({v})'


# Instruction class
@dataclass
class Instruction:
    opcode: int
    mnemonic: str
    bytes: int
    operands: list[Operand]
    immediate: bool
    cycles: list[int]

    def create(self, operands):
        return Instruction(opcode=self.opcode, immediate=self.immediate, operands=operands, cycles=self.cycles,
                           bytes=self.bytes, mnemonic=self.mnemonic)

    def setOperands(self, operands):
        self.operands = operands

    def getOperands(self):
        return self.operands

    def copy(self):
        return copy.copy(self)

    def print(self):
        ops = ', '.join(op.print() for op in self.operands)
        s = f"{self.opcode} {self.mnemonic:<8} {ops}"
        return s


# Returns unprefixed and cbprefixed opcodes dictionary
def getOpcodes(filename):
    # Open instructions
    f = open(filename)
    instructions = json.load(f)

    # Initialize instruction list
    unprefixed = []
    cbprefixed = []

    # Load instruction tables
    for ninstr in instructions["cbprefixed"]:
        instr = instructions["cbprefixed"][ninstr]
        oplist = []
        for op in instr["operands"]:
            operation = Operand(immediate=op["immediate"], name=op["name"], bytes=op.get("bytes"), value=None,
                                adjust=None)
            oplist.append(operation)
        cbprefixed.append(
            Instruction(opcode=ninstr, immediate=instr["immediate"], bytes=instr.get("bytes"), cycles=instr["cycles"],
                        mnemonic=instr["mnemonic"], operands=oplist))

    for ninstr in instructions["unprefixed"]:
        instr = instructions["unprefixed"][ninstr]
        oplist = []
        for op in instr["operands"]:
            adjust = None
            if op.get("increment"):
                adjust = "+"
            elif op.get("decrement"):
                adjust = "-"
            operation = Operand(immediate=op["immediate"], name=op["name"], bytes=op.get("bytes"), value=None,
                                adjust=adjust)
            oplist.append(operation)
        unprefixed.append(
            Instruction(opcode=ninstr, immediate=instr["immediate"], bytes=instr.get("bytes"), cycles=instr["cycles"],
                        mnemonic=instr["mnemonic"], operands=oplist))
    return unprefixed, cbprefixed
