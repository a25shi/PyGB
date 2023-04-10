import sys
from dataclasses import dataclass
from pathlib import Path
import opcode


@dataclass
class Decoder:
    # memory banks
    memory: bytes
    # program counter
    address: int
    # instructions
    unprefixed: dict
    cbprefixed: dict

    @classmethod
    def create(cls, opcodefile: str, memory: bytes, address: int = 0):
        unprefixed, cbprefixed = opcode.getOpcodes(opcodefile)
        return cls(unprefixed=unprefixed, cbprefixed=cbprefixed, memory=memory, address=address)

    # read counter num of bytes from address
    def read(self, address: int, counter: int = 1):
        if 0 <= address + counter <= len(self.memory):
            # get bytes in memory from address to address + counter
            data = self.memory[address: address + counter]
            # get int representation of bytes, with edian using system byteorder
            return int.from_bytes(data, sys.byteorder)
        else:
            raise IndexError(f'{address=}+{counter=} is out of range')

    # decodes instruction at address
    def decode(self, address: int):
