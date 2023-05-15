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
        self.decoder = Decoder('Opcodes.json', filename, address=0)

    def getVal(self, operand: Operand):
        # Op is a register
        if operand.value is None:
            # Get from register
            if operand.immediate:
                return self.registers.__getitem__(operand.name)
            # Get from memory pointer
            else:
                ptr = self.registers.__getitem__(operand.name)
                return self.decoder.get(ptr)

        # Is an immediate number or address
        else:
            if operand.immediate:
                return operand.value
            else:
                return self.decoder.get(operand.value)

    def setVal(self, operand: Operand, val):
        # Operand is an Address
        if operand.value is not None:
            self.decoder.set(operand.value, val)

        # Operand is a Register
        else:
            # if immediate, store in register
            if operand.immediate:
                self.registers.__setitem__(operand.name, val)
            # otherwise store at byte pointed by register
            else:
                ptr = self.registers.__getitem__(operand.name)
                self.decoder.set(ptr, val)

    def LD(self, operand1: Operand, operand2: Operand):
        ret = self.getVal(operand2)
        self.setVal(operand1, ret)

    def execute(self, instruction: Instruction):
        # I'm using 3.10's pattern matching, but you can use a
        # dictionary to dispatch to functions instead, or a series of
        # if statements.
        match instruction:
            case Instruction(mnemonic="NOP"):
                pass
            case Instruction(mnemonic="LD"):
                operands = instruction.getOperands()
                self.LD(operands[0], operands[1])
            case Instruction(mnemonic="LDH"):
                operands = instruction.getOperands()
                self.LD(operands[0], operands[1])
            case Instruction(mnemonic="LDI"):
                operands = instruction.getOperands()
                self.LD(operands[0], operands[1])
                self.registers["HL"] += 1
            case Instruction(mnemonic="LDD"):
                operands = instruction.getOperands()
                self.LD(operands[0], operands[1])
                self.registers["HL"] -= 1
            case Instruction(mnemonic="PUSH"):
                operand = instruction.getOperands()
                val = self.registers[operand[0].name]
                self.decoder.set(self.registers["SP"] - 1, val >> 8)
                self.decoder.set(self.registers["SP"] - 2, val & 0xFF)
                self.registers["SP"] -= 2
            case Instruction(mnemonic="POP"):
                operand = instruction.getOperands()
                val = self.decoder.get(self.registers["SP"])
                val += self.decoder.get(self.registers["SP"] + 1) << 8
                self.registers["SP"] += 2
                self.registers[operand[0].name] = val
            case Instruction(mnemonic="ADD"):
                operands = instruction.getOperands()

                # Get 1st Op value
                val = self.getVal(operands[0])

                # Get 2nd Op value
                res = self.getVal(operands[1])

                # Set flag registers HL
                if operands[0].name == "HL":
                    self.registers.__setitem__("n", 0)
                    self.registers.__setitem__("h", (val & 0xFFF) + (res & 0xFFF) > 0xFFF)
                    self.registers.__setitem__("c", (val + res) > 0xFFFF)

                    # Set register value
                    self.registers.__setitem__(operands[0].name, val + res)

                # Set flag registers SP
                elif operands[0].name == "SP":
                    self.registers.__setitem__("z", 0)
                    self.registers.__setitem__("n", 0)
                    if res >= 0:
                        self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                        self.registers.__setitem__("c", (val + res) > 0xFF)
                    else:
                        self.registers.__setitem__("h", ((val + res) & 0xF) <= (val & 0xF))
                        self.registers.__setitem__("c", ((val + res) & 0xFF) <= (val & 0xFF))
                    # Set register value
                    t = val + ((res ^ 0x80) - 0x80)
                    t &= 0xFFFF
                    self.registers.__setitem__(operands[0].name, t)

                # Set flag register A
                else:
                    self.registers.__setitem__("z", (val + res) & 0xFF == 0)
                    self.registers.__setitem__("n", 0)
                    self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                    self.registers.__setitem__("c", (val + res) > 0xFF)

                    # Set register value
                    self.registers.__setitem__(operands[0].name, val + res)

            case Instruction(mnemonic="ADC"):
                operands = instruction.getOperands()

                # Get carry flag
                carry = self.registers.__getitem__("c")

                # Get 1st Op value (A)
                val = self.getVal(operands[0])

                # 2nd Op is a register
                res = self.getVal(operands[1])

                # Do math and set value
                self.setVal(operands[0], val + res + carry)

                # Flags
                self.registers.__setitem__("z", (val + res + carry) & 0xFF == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", ((val & 0xF) + (res & 0xF) + carry) > 0xF)
                self.registers.__setitem__("c", (val + res + carry) > 0xFF)

            case Instruction(mnemonic="SUB"):
                operands = instruction.getOperands()

                val = self.getVal(operands[0])
                res = self.getVal(operands[1])
                self.setVal(operands[0], val - res)

                # Flags
                self.registers.__setitem__("z", (val - res) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", val - res < 0)

            case Instruction(mnemonic="SBC"):
                operands = instruction.getOperands()

                val = self.getVal(operands[0])
                res = self.getVal(operands[1])
                carry = self.registers.__getitem__("c")

                self.setVal(operands[0], val - res - carry)

                # Flags
                self.registers.__setitem__("z", (val - res - carry) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) - carry < 0)
                self.registers.__setitem__("c", val - res - carry < 0)

            case Instruction(mnemonic="AND"):
                operands = instruction.getOperands()
                val = self.getVal(operands[0])
                res = self.getVal(operands[1])

                self.setVal(operands[0], val & res)

                # Flags
                self.registers.__setitem__("z", (val & res) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 1)
                self.registers.__setitem__("c", 0)

            case Instruction(mnemonic="XOR"):
                operands = instruction.getOperands()
                val = self.getVal(operands[0])
                res = self.getVal(operands[1])

                self.setVal(operands[0], val ^ res)

                # Flags
                self.registers.__setitem__("z", ((val ^ res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)

            case Instruction(mnemonic="OR"):
                operands = instruction.getOperands()
                val = self.getVal(operands[0])
                res = self.getVal(operands[1])

                self.setVal(operands[0], val | res)

                # Flags
                self.registers.__setitem__("z", ((val | res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)

            case Instruction(mnemonic="CP"):
                operands = instruction.getOperands()
                val = self.getVal(operands[0])
                res = self.getVal(operands[1])

                # Flags
                self.registers.__setitem__("z", val == res)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", val < res)

            case Instruction(mnemonic="INC"):
                operand = instruction.getOperands()
                val = self.getVal(operand[0])
                self.setVal(operand[0], val + 1)

                # Flags
                self.registers.__setitem__("z", (val + 1) & 0xFF == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + 1 > 0xF)

            case Instruction(mnemonic="DEC"):
                operand = instruction.getOperands()
                val = self.getVal(operand[0])
                self.setVal(operand[0], val - 1)

                # Flags
                self.registers.__setitem__("z", val - 1 == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - 1 < 0xF)

            case Instruction(mnemonic="DAA"):
                pass
            case Instruction(mnemonic="CPL"):
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
