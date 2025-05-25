from dataclasses import dataclass
import opcodes
from cartridge import CartridgeMetadata
from memory import Memory
from pathlib import Path


@dataclass
class Decoder:
    # game data
    memory: Memory
    # program counter
    address: int
    # instructions
    unprefixed: dict
    cbprefixed: dict

    def __init__(self, opcodefile: str, filename: str, metadata: CartridgeMetadata, cpu, address: int = 0,):
        self.unprefixed, self.cbprefixed = opcodes.getOpcodes(opcodefile)
        self.memory = Memory(Path(filename).read_bytes(), metadata.cartridge_type, cpu)
        self.address = address

    # get bytes from memory
    def get(self, address: int, counter: int = 1):
        return self.memory.get(address, counter)

    # set bytes at memory
    def set(self, address: int, value: int):
        self.memory.set(address, value)

    # decodes instruction at address
    def decode(self, address: int):
        # opcode = item at pc
        opcode = self.get(address)
        # iterate pc
        address += 1
        # if prefixed opcode, read next item and get cb instruction
        if opcode == 0xCB:
            opcode = self.get(address)
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
                val = self.get(address, operand.bytes)
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


def disassemble(decoder: Decoder, address, count: int):
    for _ in range(count):
        try:
            new_address, instruction = decoder.decode(address)
            pp = instruction.print()
            print(f'{address:>04X} {pp}')
            address = new_address
        except IndexError as e:
            print('ERROR - {e!s}')
            break
