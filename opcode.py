from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import json
import cartridge

# Operand class
@dataclass(frozen=True)
class Operand:
    immediate: bool
    name: str
    bytes: int
    value: int | None
    adjust: Literal["+", "-"] | None

    def create(self, value):
        return Operand(immediate=self.immediate, name=self.name, bytes=self.bytes, value=value, adjust=self.adjust)

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


# Open instructions
f = open('Opcodes.json')
instructions = json.load(f)

# Initialize instruction list
unprefixed = []
cbprefixed = []

# Load instruction tables
for ninstr in instructions["cbprefixed"]:
    instr = instructions["cbprefixed"][ninstr]
    oplist = []
    for op in instr["operands"]:
        operation = Operand(immediate=op["immediate"], name=op["name"], bytes=op.get("bytes"), value=None, adjust=None)
        oplist.append(operation)
    cbprefixed.append(
        Instruction(opcode=ninstr, immediate=instr["immediate"], bytes=instr.get("bytes"), cycles=instr["cycles"],
                    mnemonic=instr["mnemonic"], operands=oplist))

for ninstr in instructions["unprefixed"]:
    instr = instructions["unprefixed"][ninstr]
    oplist = []
    for op in instr["operands"]:
        operation = Operand(immediate=op["immediate"], name=op["name"], bytes=op.get("bytes"), value=None, adjust=None)
        oplist.append(operation)
    unprefixed.append(
        Instruction(opcode=ninstr, immediate=instr["immediate"], bytes=instr.get("bytes"), cycles=instr["cycles"],
                    mnemonic=instr["mnemonic"], operands=oplist))

return ()