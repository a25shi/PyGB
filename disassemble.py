import sys
from dataclasses import dataclass
import opcodes


@dataclass
class Decoder:
    # game data
    memory: bytes
    # program counter
    address: int
    # instructions
    unprefixed: dict
    cbprefixed: dict

    def __init__(self, opcodefile: str, memory: bytes, address: int = 0):
        self.unprefixed, self.cbprefixed = opcodes.getOpcodes(opcodefile)
        self.memory = memory
        self.address = address

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
        # opcode = item at pc
        opcode = self.read(address)
        # iterate pc
        address += 1
        # if prefixed opcode, read next item and get cb instruction
        if opcode == 0xCB:
            opcode = self.read(address)
            address += 1
            instruction = self.cbprefixed[opcode]
        # if not, get instruction normally
        else:
            instruction = self.unprefixed[opcode]

        # operand array
        oparr = []

        # for each operand in instruction operand
        for operand in instruction.operands:
            # if bytes its a memory address, and read the bytes
            if operand.bytes is not None:
                # read memory value
                val = self.read(address, operand.bytes)
                address += operand.bytes
                # create operand copy with value stored
                newop = operand.copy()
                newop.setValue(val)
                oparr.append(newop)
            # if no bytes, not memory address
            else:
                oparr.append(operand)
        # Copy instruction and set new operands
        ret_instr = instruction.copy()
        ret_instr.setOperands(oparr)
        return address, ret_instr

    def getSize(self):
        return len(self.memory)


def disassemble(decoder: Decoder, address: int, count: int):
    for _ in range(count):
        try:
            new_address, instruction = decoder.decode(address)
            pp = instruction.print()
            print(f'{address:>04X} {pp}')
            address = new_address
        except IndexError as e:
            print('ERROR - {e!s}')
            break
