from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Operand:
    immediate: bool
    name: str
    bytes: int
    value: int | None
    adjust: Literal["+", "-"] | None

    def create(self, value):
        return Operand (immediate=self.immediate, name=self.name, bytes=self.bytes, value=value, adjust=self.adjust)


@dataclass
class Instruction:
    opcode: int
    mnemonic: str
    bytes: int
    operands: list[Operand]
    immediate: bool
    cycles: list[int]

