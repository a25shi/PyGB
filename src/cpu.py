import sys
from collections.abc import MutableMapping
from dataclasses import dataclass
from disassemble import Decoder
from opcodes import Instruction, Operand
from timer import Timer
from screen import Screen

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
            setattr(self, register, (current_value & 0xFF00 | value & 0x00FF) & 0xFFFF)
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

    def __init__(self, filename, metadata):
        self.registers = Registers(AF=0, BC=0, DE=0, HL=0, PC=0, SP=0)
        self.decoder = Decoder('Opcodes.json', filename, metadata, address=0, cpu=self)
        self.maxcycles = 69905  # CPU clocks per second (4194304) / fixed number of frames we want
        self.i_master = 0
        self.i_enable = 0
        self.i_flag = 0
        self.timer = Timer()
        self.screen = Screen(self)
        self.blargg = ""

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

    def RET(self):
        sp = self.registers.__getitem__("SP")
        pc = self.decoder.get((sp + 1) & 0xFFFF) << 8
        pc |= self.decoder.get(sp)
        self.registers.__setitem__("PC", pc)
        sp += 2
        self.registers.__setitem__("SP", sp)

    def CALL(self, val):
        sp = self.registers.__getitem__("SP")
        pc = self.registers.__getitem__("PC")
        self.decoder.set((sp - 1) & 0xFFFF, pc >> 8)
        self.decoder.set((sp - 2) & 0xFFFF, pc & 0xFF)
        self.registers.__setitem__("PC", val)
        self.registers.__setitem__("SP", sp - 2)

    def execute(self, instruction: Instruction):

        match instruction:
            case Instruction(mnemonic="NOP"):
                pass

            case Instruction(mnemonic="LD"):
                operands = instruction.getOperands()

                # special case LD (C),A
                if instruction.opcode == "0xE2":
                    # (C)
                    ptr = self.registers["C"]
                    a = self.registers["A"]
                    # (C + 0xFF00) = A
                    self.decoder.set(ptr + 0xFF00, a)
                    return instruction.cycles[0]

                # special case LD A, (C)
                elif instruction.opcode == "0xF2":
                    # (C)
                    ptr = self.registers["C"]
                    item = self.decoder.get(ptr + 0xFF00)
                    # A = (C + 0xFF00)
                    self.registers["A"] = item
                    return instruction.cycles[0]
                # special case LD HL,SP+r8
                elif instruction.opcode == "0xF8":
                    res = self.getVal(operands[2])
                    val = self.registers["SP"]

                    # HL = SP + r8
                    self.registers["HL"] = val + ((res ^ 0x80) - 0x80)

                    # Flags
                    self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                    self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) > 0xFF)
                    return instruction.cycles[0]

                self.LD(operands[0], operands[1])
                # check for inc or dec
                if operands[0].adjust:
                    if operands[0].adjust == "+":
                        self.registers["HL"] += 1
                    else:
                        self.registers["HL"] -= 1

                elif operands[1].adjust:
                    if operands[1].adjust == "+":
                        self.registers["HL"] += 1
                    else:
                        self.registers["HL"] -= 1

            case Instruction(mnemonic="LDH"):
                operands = instruction.getOperands()

                # special case LDH A,(a8)
                if instruction.opcode == "0xF0":
                    # (a8)
                    ptr = operands[1].value
                    item = self.decoder.get(ptr + 0xFF00)
                    # A = (a8 + ff00)
                    self.registers["A"] = item
                    return instruction.cycles[0]

                # special case LDH (a8), A
                elif instruction.opcode == "0xE0":
                    # (a8)
                    ptr = operands[0].value
                    a = self.registers["A"]
                    # (a8 + 0xFF00) = A
                    self.decoder.set(ptr + 0xFF00, a)
                    return instruction.cycles[0]

                self.LD(operands[0], operands[1])

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
                    self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) > 0xFFFF)

                    # Set register value
                    self.registers.__setitem__(operands[0].name, val + res)

                # Set flag registers SP
                elif operands[0].name == "SP":
                    self.registers.__setitem__("z", 0)
                    self.registers.__setitem__("n", 0)

                    self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                    self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) > 0xFF)

                    # Set register value
                    t = val + ((res ^ 0x80) - 0x80)
                    t &= 0xFFFF
                    self.registers.__setitem__(operands[0].name, t)

                # Set flag register A
                else:
                    self.registers.__setitem__("z", (val + res) & 0xFF == 0)
                    self.registers.__setitem__("n", 0)
                    self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                    self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) > 0xFF)

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
                self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) + (carry & 0xFF) > 0xFF)

            case Instruction(mnemonic="SUB"):
                operands = instruction.getOperands()

                val = self.registers.__getitem__("A")
                res = self.getVal(operands[0])
                self.registers.__setitem__("A", val - res)

                # Flags
                self.registers.__setitem__("z", (val - res) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) < 0)

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
                self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) - (carry & 0xFF) < 0)

            case Instruction(mnemonic="AND"):
                operands = instruction.getOperands()

                val = self.registers.__getitem__("A")
                res = self.getVal(operands[0])
                self.registers.__setitem__("A", val & res)

                # Flags
                self.registers.__setitem__("z", (val & res) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 1)
                self.registers.__setitem__("c", 0)

            case Instruction(mnemonic="XOR"):
                operands = instruction.getOperands()

                val = self.registers.__getitem__("A")
                res = self.getVal(operands[0])
                self.registers.__setitem__("A", val ^ res)

                # Flags
                self.registers.__setitem__("z", ((val ^ res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)

            case Instruction(mnemonic="OR"):
                operands = instruction.getOperands()

                val = self.registers.__getitem__("A")
                res = self.getVal(operands[0])
                self.registers.__setitem__("A", val | res)

                # Flags
                self.registers.__setitem__("z", ((val | res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)

            case Instruction(mnemonic="CP"):
                operands = instruction.getOperands()

                val = self.registers.__getitem__("A")
                res = self.getVal(operands[0])

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
                if instruction.opcode not in ["0x03", "0x13", "0x23", "0x33"]:
                    self.registers.__setitem__("z", (val + 1) & 0xFF == 0)
                    self.registers.__setitem__("n", 0)
                    self.registers.__setitem__("h", (val & 0xF) + 1 > 0xF)

            case Instruction(mnemonic="DEC"):
                operand = instruction.getOperands()
                val = self.getVal(operand[0])
                self.setVal(operand[0], val - 1)

                # Flags
                if instruction.opcode not in ["0x0B", "0x1B", "0x2B", "0x3B"]:
                    self.registers.__setitem__("z", val - 1 == 0)
                    self.registers.__setitem__("n", 1)
                    self.registers.__setitem__("h", ((val & 0xF) - (1 & 0xF)) < 0)


            case Instruction(mnemonic="DAA"):
                a = self.registers.__getitem__("A")
                n = self.registers.__getitem__("n")
                c = self.registers.__getitem__("c")
                h = self.registers.__getitem__("h")

                if not n:
                    if c or a > 0x99:
                        a += 0x60
                        self.registers.__setitem__("c", 1)
                    if h or (a & 0x0f) > 0x09:
                        a += 0x6
                else:
                    if c:
                        a -= 0x60
                    if h:
                        a -= 0x6

                self.registers.__setitem__("A", a)
                self.registers.__setitem__("z", a == 0)
                self.registers.__setitem__("h", 0)

            case Instruction(mnemonic="CPL"):
                self.registers.__setitem__("A", ~self.registers.__getitem__("A"))
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", 1)

            case Instruction(mnemonic="RLCA"):
                a = self.registers.__getitem__("A")
                val = (a << 1) + (a >> 7)

                # Flags
                self.registers.__setitem__("z", 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.registers.__setitem__("A", val)

            case Instruction(mnemonic="RLA"):
                a = self.registers.__getitem__("A")
                c = self.registers.__getitem__("c")
                val = (a << 1) + c

                # Flags
                self.registers.__setitem__("z", 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.registers.__setitem__("A", val)

            case Instruction(mnemonic="RRCA"):
                a = self.registers.__getitem__("A")

                val = (a >> 1) + ((a & 1) << 7) + ((a & 1) << 8)

                # Flags
                self.registers.__setitem__("z", 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.registers.__setitem__("A", val)

            case Instruction(mnemonic="RRA"):
                a = self.registers.__getitem__("A")
                c = self.registers.__getitem__("c")
                val = (a >> 1) + (c << 7) + ((a & 1) << 8)

                # Flags
                self.registers.__setitem__("z", 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.registers.__setitem__("A", val)

            case Instruction(mnemonic="RLC"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                val = (reg << 1) + (reg >> 7)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="RL"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                c = self.registers.__getitem__("c")
                val = (reg << 1) + c

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="RRC"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])

                val = (reg >> 1) + ((reg & 1) << 7) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="RR"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                c = self.registers.__getitem__("c")
                val = (reg >> 1) + (c << 7) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="SLA"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                val = reg << 1

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="SWAP"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                val = ((reg & 0xF0) >> 4) | ((reg & 0x0F) << 4)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="SRA"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                val = ((reg >> 1) | (reg & 0x80)) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="SRL"):
                operand = instruction.getOperands()
                reg = self.getVal(operand[0])
                val = (reg >> 1) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                self.setVal(operand[0], val)

            case Instruction(mnemonic="BIT"):
                operands = instruction.getOperands()
                shift = self.getVal(operands[0])
                reg = self.getVal(operands[1])
                val = reg & (1 << shift)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 1)

            case Instruction(mnemonic="SET"):
                operands = instruction.getOperands()
                shift = self.getVal(operands[0])
                reg = self.getVal(operands[1])
                val = reg | (1 << shift)
                self.setVal(operands[1], val)

            case Instruction(mnemonic="RES"):
                operands = instruction.getOperands()
                shift = int(operands[0].name)
                reg = self.getVal(operands[1])
                val = reg & ~(1 << shift)
                self.setVal(operands[1], val)

            case Instruction(mnemonic="CCF"):
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", not self.registers.__getitem__("c"))

            case Instruction(mnemonic="SCF"):
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 1)

            case Instruction(mnemonic="HALT"):
                raise InstructionError(f"Cannot execute {instruction}")

            case Instruction(mnemonic="STOP"):
                raise InstructionError(f"Cannot execute {instruction}")

            case Instruction(mnemonic="DI"):
                self.i_master = False

            case Instruction(mnemonic="EI"):
                self.i_master = True

            case Instruction(mnemonic="JP"):
                operands = instruction.getOperands()

                # unconditional
                if len(operands) == 1:
                    val = self.getVal(operands[0])
                    self.registers.__setitem__("PC", val)

                # conditional
                else:
                    condition = operands[0].name
                    val = self.getVal(operands[1])
                    if condition == "C" and self.registers.__getitem__("c"):
                        self.registers.__setitem__("PC", val)
                    elif condition == "NC" and not self.registers.__getitem__("c"):
                        self.registers.__setitem__("PC", val)
                    elif condition == "Z" and self.registers.__getitem__("z"):
                        self.registers.__setitem__("PC", val)
                    elif condition == "NZ" and not self.registers.__getitem__("z"):
                        self.registers.__setitem__("PC", val)
                    else:
                        return instruction.cycles[1]

            case Instruction(mnemonic="JR"):
                operands = instruction.getOperands()

                # unconditional
                if len(operands) == 1:
                    val = self.getVal(operands[0])
                    pc = self.registers.__getitem__("PC")
                    pc += ((val ^ 0x80) - 0x80)
                    self.registers.__setitem__("PC", pc)

                # conditional
                else:
                    condition = operands[0].name
                    val = self.getVal(operands[1])
                    pc = self.registers.__getitem__("PC")
                    pc += ((val ^ 0x80) - 0x80)
                    if condition == "C" and self.registers.__getitem__("c"):
                        self.registers.__setitem__("PC", pc)
                    elif condition == "NC" and not self.registers.__getitem__("c"):
                        self.registers.__setitem__("PC", pc)
                    elif condition == "Z" and self.registers.__getitem__("z"):
                        self.registers.__setitem__("PC", pc)
                    elif condition == "NZ" and not self.registers.__getitem__("z"):
                        self.registers.__setitem__("PC", pc)
                    else:
                        return instruction.cycles[1]

            case Instruction(mnemonic="CALL"):
                operands = instruction.getOperands()
                if len(operands) == 1:
                    val = self.getVal(operands[0])
                    self.CALL(val)
                else:
                    condition = operands[0].name
                    val = self.getVal(operands[1])
                    if condition == "C" and self.registers.__getitem__("c"):
                        self.CALL(val)
                    elif condition == "NC" and not self.registers.__getitem__("c"):
                        self.CALL(val)
                    elif condition == "Z" and self.registers.__getitem__("z"):
                        self.CALL(val)
                    elif condition == "NZ" and not self.registers.__getitem__("z"):
                        self.CALL(val)
                    else:
                        return instruction.cycles[1]

            case Instruction(mnemonic="RET"):
                operand = instruction.getOperands()
                if len(operand):
                    condition = operand[0].name
                    if condition == "C" and self.registers.__getitem__("c"):
                        self.RET()
                    elif condition == "NC" and not self.registers.__getitem__("c"):
                        self.RET()
                    elif condition == "Z" and self.registers.__getitem__("z"):
                        self.RET()
                    elif condition == "NZ" and not self.registers.__getitem__("z"):
                        self.RET()
                    else:
                        return instruction.cycles[1]
                else:
                    self.RET()

            case Instruction(mnemonic="RETI"):
                raise InstructionError(f"Cannot execute {instruction}")

            case Instruction(mnemonic="RST"):
                operands = instruction.getOperands()
                val = operands[0].name
                val = int(val.rstrip('H'), 16)
                self.CALL(val)

            case _:
                raise InstructionError(f"Cannot execute {instruction}")

        return instruction.cycles[0]

    def run(self):
        while True:
            self.update()

    def update(self):
        c_cycles = 0
        while c_cycles < self.maxcycles:
            # blargg debug
            self.blargg_update()
            self.blargg_print()

            # execute
            cycles = self.executeNextOp()
            c_cycles += cycles

            # tick timer
            timer_inter = self.timer.tick(cycles)
            if timer_inter:
                self.setInterrupt(2)

            # update graphics
            self.screen.update(cycles)

            # check interrupts
            self.checkInterrupt()

    def executeNextOp(self):
        address = self.registers["PC"]
        try:
            next_address, instruction = self.decoder.decode(address)
            print(f'{address:>04X} {instruction.print()}')
        except IndexError:
            raise InstructionError(f"Cannot execute on {address}")
        self.registers["PC"] = next_address
        cycles = self.execute(instruction)
        return cycles

    def setInterrupt(self, bit):
        flag = 1 << bit
        self.i_flag |= flag

    def checkInterrupt(self):
        total = (self.i_enable & 0b11111) & (self.i_flag & 0b11111)
        if total:
            # interrupt master check
            if self.i_master:
                # V_BLANK
                if total & 0b1:
                    self.handleInterrupt(0b1, 0x40)
                # LCD
                elif total & 0b10:
                    self.handleInterrupt(0b10, 0x48)
                # TIMER
                elif total & 0b100:
                    self.handleInterrupt(0b100, 0x50)
                # SERIAL
                elif total & 0b1000:
                    self.handleInterrupt(0b1000, 0x58)
                # JOYPAD
                elif total & 0b10000:
                    self.handleInterrupt(0b10000, 0x60)

    def handleInterrupt(self, flag, address):
        self.i_flag ^= flag  # remove flag

        self.decoder.set(self.registers["SP"] - 1, self.registers["PC"] >> 8)
        self.decoder.set(self.registers["SP"] - 2, self.registers["PC"] & 0xFF)
        self.registers["SP"] -= 2

        self.registers["PC"] = address
        self.i_master = False

    def blargg_update(self):
        if self.decoder.get(0xFF02) == 0x81:
            val = chr(self.decoder.get(0xFF01))
            self.blargg += val
            self.decoder.set(0xFF02, 0)

    def blargg_print(self):
        if self.blargg:
            print(self.blargg)
