from collections.abc import MutableMapping
from dataclasses import dataclass
from disassemble import Decoder
from opcodes import Instruction, Operand
from memory import Memory
from pathlib import Path

# Constants
REGISTERS_LOW = {"F": "AF", "C": "BC", "E": "DE", "L": "HL"}
REGISTERS_HIGH = {"A": "AF", "B": "BC", "D": "DE", "H": "HL"}
REGISTERS = {"AF", "BC", "DE", "HL", "PC", "SP"}
FLAGS = {"c": 4, "h": 5, "n": 6, "z": 7}


class InstructionError(Exception):
    pass


# Registers
@dataclass
class Registers(MutableMapping):
    AF: int
    BC: int
    DE: int
    HL: int
    PC: int
    SP: int

    def values(self):
        return [self.AF, self.BC, self.DE, self.HL, self.PC, self.SP]

    def __iter__(self):
        return iter(self.values())

    def __len__(self):
        return len(self.values())

    def __setitem__(self, key, value):
        if key in REGISTERS_HIGH:
            register = REGISTERS_HIGH[key]
            current_value = self[register]
            setattr(self, register, (current_value & 0x00FF | (value << 8)) & 0xFFFF)
        elif key in REGISTERS_LOW:
            register = REGISTERS_LOW[key]
            current_value = self[register]
            setattr(self, register, (current_value & 0xFF00 | value) & 0xFFFF)
        elif key in FLAGS:
            assert value in (0, 1), f"{value} must be 0 or 1"
            flag_bit = FLAGS[key]
            if value == 0:
                self.AF = self.AF & ~(1 << flag_bit)
            else:
                self.AF = self.AF | (1 << flag_bit)
        else:
            if key in REGISTERS:
                setattr(self, key, value & 0xFFFF)
            else:
                raise KeyError(f"No such register {key}")

    def __delitem__(self, key):
        raise NotImplementedError("Register deletion is not supported")

    def __getitem__(self, key):
        # Shift 8 bits to get high bits in register
        if key in REGISTERS_HIGH:
            register = REGISTERS_HIGH[key]
            return getattr(self, register) >> 8
        # Compare to get lower bits in register
        elif key in REGISTERS_LOW:
            register = REGISTERS_LOW[key]
            return getattr(self, register) & 0xFF
        # Shift [Flag] bits to get flag, and check if flag is set
        elif key in FLAGS:
            flag_bit = FLAGS[key]
            return self.AF >> flag_bit & 1
        # Else get whole register
        else:
            if key in REGISTERS:
                return getattr(self, key)
            else:
                raise KeyError(f"No such register {key}")


class CPU:

    def __init__(self, filename):
        self.registers = Registers(AF=0, BC=0, DE=0, HL=0, PC=0, SP=0)
        self.memory = Memory()
        self.decoder = Decoder('Opcodes.json', Path(filename).read_bytes(), address=0)

    def set(self, operand1: Operand, operand2: Operand):
        ret = None

        # Operand2 is an Address or Immediate
        if operand2.value is not None:
            if operand2.immediate:
                ret = operand2.value
            else:
                ret = self.memory.get(operand2.value)

        # Operand2 is a Register
        else:
            # Get value at Register
            ret = self.registers.__getitem__(operand2.name)

            # If register is not marked as immediate, means get value at where register is pointing
            if not operand2.immediate:
                ret = self.memory.get(ret)

        # Operand1 is an Address
        if operand1.value is not None:
            self.memory.set(operand1.value, ret)

        # Operand1 is a Register
        else:
            # if immediate, store in register
            if operand1.immediate:
                self.registers.__setitem__(operand1.name, ret)
            # otherwise store at byte pointed by register
            else:
                temp = self.registers.__getitem__(operand1.name)
                self.memory.set(temp, ret)

    def execute(self, instruction: Instruction):
        # I'm using 3.10's pattern matching, but you can use a
        # dictionary to dispatch to functions instead, or a series of
        # if statements.
        match instruction:
            case Instruction(mnemonic="NOP"):
                pass
            case Instruction(mnemonic="LD"):
                operands = instruction.getOperands()
                self.set(operands[0], operands[1])
            case Instruction(mnemonic="LDI"):

                pass
            case Instruction(mnemonic="LDD"):
                pass
            case _:
                raise InstructionError(f"Cannot execute {instruction}")

    def run(self):
        while True:
            address = self.registers["PC"]
            try:
                next_address, instruction = self.decoder.decode(address)
            except IndexError:
                break
            self.registers["PC"] = next_address
            self.execute(instruction)
