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
    unprefixed: list
    cbprefixed: list

    def __init__(self, opcodefile: str, filename: str, metadata: CartridgeMetadata, cpu, address):
        self.unprefixed, self.cbprefixed = opcodes.getOpcodes(opcodefile)
        self.memory = Memory(Path(filename).read_bytes(), metadata, cpu)
        self.address = address

    # get bytes from memory
    def getMem(self, address, counter = 1):
        return self.memory.get(address, counter)

    # set bytes at memory
    def setMem(self, address, value):
        self.memory.set(address, value)

    # decodes instruction at address
    def decode(self, address):
        # opcode = item at pc
        opcode = self.getMem(address)
        cbbool = False
        # iterate pc
        address += 1
        # if prefixed opcode, read next item and get cb instruction
        if opcode == 0xCB:
            opcode = self.getMem(address)
            address += 1
            instruction = self.cbprefixed[opcode]
            cbbool = True
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
                val = self.getMem(address, operand.bytes)
                address += operand.bytes
                # create operand copy with value stored
                operand.setValue(val)
                oparr.append(operand)
            # if no bytes, not memory address
            else:
                oparr.append(operand)
        # Copy instruction and set new operands
        instruction.setOperands(oparr)
        return Wrapper(address, instruction, cbbool)

# exists only to return instruction object since Cython doesn't allow objects in tuples
class Wrapper:
    address: int
    instruction: object
    cbbool: bool
    def __init__(self, a, b, c):
        self.address = a
        self.instruction = b
        self.cbbool = c

def disassemble(decoder: Decoder, address, count):
    for _ in range(count):
        try:
            wrapper = decoder.decode(address)
            new_address, instruction, cb = wrapper.address, wrapper.instruction, wrapper.cbbool
            pp = instruction.print()
            print(f'{address:>04X} {pp}')
            address = new_address
        except IndexError as e:
            print('ERROR - {e!s}')
            break
