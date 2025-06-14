import sys
import os
import time
from registers import Registers
from disassemble import Decoder
from opcodes import Instruction, Operand
from joypad import Joypad
from timer import Timer
from screen import Screen
import pygame
# from __pypy__ import newlist_hint
# cython: annotation_typing = False

import cython
if cython.compiled:
    print("Yep, I'm compiled.")
else:
    print("Just a lowly interpreted script.")

class InstructionError(Exception):
    pass

class CPU:
    def __init__(self, filename, metadata):
        self.registers = Registers(AF=0, BC=0, DE=0, HL=0, PC=0, SP=0)
        self.decoder = Decoder(os.path.join(os.path.dirname(__file__), 'Opcodes.json'), filename, metadata, address=0, cpu=self)
        self.maxcycles = 69905  # CPU clocks per second (4194304) / fixed number of frames we want
        self.i_master = 0
        self.i_enable = 0
        self.i_flag = 0
        self.i_queue = False
        self.timer = Timer()
        self.screen = Screen(self)
        self.joypad = Joypad()
        self.blargg = ""
        self.halt = False
        self.sync_cycles = 0
        self.cycles = 0
    def initVals(self):
        self.registers.__setitem__("AF", 0x01B0)
        self.registers.__setitem__("BC", 0x0013)
        self.registers.__setitem__("DE", 0x00D8)
        self.registers.__setitem__("HL", 0x014D)
        self.registers.__setitem__("SP", 0xFFFE)
        self.registers.__setitem__("PC", 0x0100)
        self.decoder.setMem(0xFF05, 0x00)
        self.decoder.setMem(0xFF06, 0x00)
        self.decoder.setMem(0xFF07, 0x00)
        self.decoder.setMem(0xFF10, 0x80)
        self.decoder.setMem(0xFF11, 0xBF)
        self.decoder.setMem(0xFF12, 0xF3)
        self.decoder.setMem(0xFF14, 0xBF)
        self.decoder.setMem(0xFF16, 0x3F)
        self.decoder.setMem(0xFF17, 0x00)
        self.decoder.setMem(0xFF19, 0xBF)
        self.decoder.setMem(0xFF1A, 0x7F)
        self.decoder.setMem(0xFF1B, 0xFF)
        self.decoder.setMem(0xFF1C, 0x9F)
        self.decoder.setMem(0xFF1E, 0xBF)
        self.decoder.setMem(0xFF20, 0xFF)
        self.decoder.setMem(0xFF21, 0x00)
        self.decoder.setMem(0xFF22, 0x00)
        self.decoder.setMem(0xFF23, 0xBF)
        self.decoder.setMem(0xFF24, 0x77)
        self.decoder.setMem(0xFF25, 0xF3)
        self.decoder.setMem(0xFF26, 0xF1)
        self.decoder.setMem(0xFF40, 0x91)
        self.decoder.setMem(0xFF42, 0x00)
        self.decoder.setMem(0xFF43, 0x00)
        self.decoder.setMem(0xFF45, 0x00)
        self.decoder.setMem(0xFF47, 0xFC)
        self.decoder.setMem(0xFF48, 0xFF)
        self.decoder.setMem(0xFF48, 0xFF)
        self.decoder.setMem(0xFF49, 0xFF)
        self.decoder.setMem(0xFF4A, 0x00)
        self.decoder.setMem(0xFF4B, 0x00)
        self.decoder.setMem(0xFFFF, 0x00)
    def POP(self, operand: Operand):
        val = self.decoder.getMem(self.registers["SP"], 2)
        self.registers["SP"] += 2
        self.registers[operand.name] = val
    def PUSH(self, operand: Operand):
        val = self.registers[operand.name]
        self.decoder.setMem(self.registers["SP"] - 1, val >> 8)
        self.decoder.setMem(self.registers["SP"] - 2, val & 0xFF)
        self.registers["SP"] -= 2
    def JP(self, value):
        self.registers["PC"] = value
    def CP(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        # Flags
        self.registers.__setitem__("z", val == res)
        self.registers.__setitem__("n", 1)
        self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
        self.registers.__setitem__("c", val < res)
    def XOR(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        self.registers["A"] = val ^ res

        # Flags
        self.registers.__setitem__("z", ((val ^ res) & 0xFF) == 0)
        self.registers.__setitem__("n", 0)
        self.registers.__setitem__("h", 0)
        self.registers.__setitem__("c", 0)
    def SBC(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        carry = self.registers.__getitem__("c")
        # Flags
        self.registers.__setitem__("z", (val - res - carry) & 0xFF == 0)
        self.registers.__setitem__("n", 1)
        self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) - carry < 0)
        self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) - (carry & 0xFF) < 0)
        # set
        self.registers["A"] = val - res - carry
    def ADC(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        carry = self.registers["c"]
        # flags
        self.registers["z"] = (val + res + carry) & 0xFF == 0
        self.registers.__setitem__("n", 0)
        self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) + carry > 0xF)
        self.registers.__setitem__("c", val + res + carry > 0xFF)
        # Set register value
        self.registers["A"] = val + res + carry
    def OR(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        self.registers["A"] = val | res


        # Flags
        self.registers.__setitem__("z", ((val | res) & 0xFF) == 0)
        self.registers.__setitem__("n", 0)
        self.registers.__setitem__("h", 0)
        self.registers.__setitem__("c", 0)
    def AND(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        self.registers["A"] = val & res

        # Flags
        self.registers.__setitem__("z", (val & res) == 0)
        self.registers.__setitem__("n", 0)
        self.registers.__setitem__("h", 1)
        self.registers.__setitem__("c", 0)
    def DEC(self, operand: Operand):
        val = self.registers[operand.name]
        self.registers[operand.name] -= 1
        # flags
        self.registers.__setitem__("z", (val - 1) & 0xFF == 0)
        self.registers.__setitem__("n", 1)
        self.registers.__setitem__("h", ((val & 0xF) - 1) < 0)

    def INC(self, operand: Operand):
        val = self.registers[operand.name]
        self.registers[operand.name] += 1
        # flags
        self.registers.__setitem__("z", (val + 1) & 0xFF == 0)
        self.registers.__setitem__("n", 0)
        self.registers.__setitem__("h", (val & 0xF) + 1 > 0xF)

    def ADD(self, operand1: Operand, operand2: Operand):
        val = self.registers[operand1.name]
        res = self.registers[operand2.name]
        # flags
        self.registers["z"] = ((val + res) & 0xFF) == 0
        self.registers.__setitem__("n", 0)
        self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
        self.registers.__setitem__("c", val + res > 0xFF)
        # Set register value
        self.registers[operand1.name] = val + res

    def SUB(self, operand: Operand):
        val = self.registers["A"]
        res = self.registers[operand.name]
        # Flags
        self.registers.__setitem__("z", (val - res) & 0xFF == 0)
        self.registers.__setitem__("n", 1)
        self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
        self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) < 0)
        # set
        self.registers["A"] = val - res

    def JR(self, operand):
        self.registers["PC"] += ((operand.value ^ 0x80) - 0x80)

    def RET(self):
        sp = self.registers["SP"]
        pc = self.decoder.getMem((sp + 1) & 0xFFFF) << 8
        pc |= self.decoder.getMem(sp)
        sp += 2
        self.registers["PC"] = pc
        self.registers["SP"] = sp

    def CALL(self, val):
        sp = self.registers.__getitem__("SP")
        pc = self.registers.__getitem__("PC")
        self.decoder.setMem((sp - 1) & 0xFFFF, pc >> 8)
        self.decoder.setMem((sp - 2) & 0xFFFF, pc & 0xFF)
        self.registers.__setitem__("PC", val)
        self.registers.__setitem__("SP", sp - 2)

    def execute(self, instruction: Instruction, cb):
        opcode = instruction.opcode
        operands = instruction.getOperands()
        if cb:
            if instruction.mnemonic == "BIT":
                if operands[1].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[1].name]
                shift = int(operands[0].name)
                val = reg & (1 << shift)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 1)
            elif instruction.mnemonic == "RES":
                if operands[1].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[1].name]

                shift = int(operands[0].name)
                val = reg & ~(1 << shift)
                if operands[1].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[1].name] = val

            elif instruction.mnemonic == "SET":
                if operands[1].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[1].name]

                shift = int(operands[0].name)
                val = reg | (1 << shift)

                if operands[1].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[1].name] = val
            elif instruction.mnemonic == "SRL":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]

                val = (reg >> 1) + ((reg & 1) << 8)
                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)
                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val
            elif instruction.mnemonic == "SWAP":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                val = ((reg & 0xF0) >> 4) | ((reg & 0x0F) << 4)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val
            elif instruction.mnemonic == "SRA":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                val = ((reg >> 1) | (reg & 0x80)) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val
            elif instruction.mnemonic == "SLA":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                val = reg << 1

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val
            elif instruction.mnemonic == "RR":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                c = self.registers.__getitem__("c")
                val = (reg >> 1) + (c << 7) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val
            elif instruction.mnemonic == "RL":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                c = self.registers.__getitem__("c")
                val = (reg << 1) + c

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val

            elif instruction.mnemonic == "RRC":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                val = (reg >> 1) + ((reg & 1) << 7) + ((reg & 1) << 8)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val
            elif instruction.mnemonic == "RLC":
                if operands[0].name == "HL":
                    self.cycles += 4
                    reg = self.decoder.getMem(self.registers["HL"])
                else:
                    reg = self.registers[operands[0].name]
                val = (reg << 1) + (reg >> 7)

                # Flags
                self.registers.__setitem__("z", (val & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)

                # Set
                val &= 0xFF
                if operands[0].name == "HL":
                    self.cycles += 4
                    self.decoder.setMem(self.registers["HL"], val)
                else:
                    self.registers[operands[0].name] = val

            else:
                raise InstructionError(f"Instruction {instruction} not yet implemented")
        else:
            if opcode == 0x00:
                pass
            elif opcode == 0x01:
                self.registers["BC"] = operands[1].value
            elif opcode == 0x02:
                ptr = self.registers["BC"]
                self.decoder.setMem(ptr, self.registers["A"])
            elif opcode == 0x03:
                self.registers["BC"] += 1
            elif opcode == 0x04:
                self.INC(operands[0])
            elif opcode == 0x05:
                self.DEC(operands[0])
            elif opcode == 0x06:
                self.registers["B"] = operands[1].value
            elif opcode == 0x07:
                a = self.registers["A"]
                val = (a << 1) + (a >> 7)
                # Flags
                self.registers.__setitem__("z", 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)
                # Set
                val &= 0xFF
                self.registers["A"] = val
            elif opcode == 0x08:
                ptr = operands[0].value
                sp = self.registers["SP"]
                self.decoder.setMem(ptr, sp & 0xFF)
                self.decoder.setMem(ptr + 1, sp >> 8)
            elif opcode == 0x09:
                val = self.registers["HL"]
                res = self.registers["BC"]
                # flags
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xFFF) + (res & 0xFFF) > 0xFFF)
                self.registers.__setitem__("c", val + res > 0xFFFF)
                # Set register value
                self.registers["HL"] = val + res
            elif opcode == 0x0A:
                ptr = self.registers["BC"]
                self.registers["A"] = self.decoder.getMem(ptr)
            elif opcode == 0x0B:
                self.registers["BC"] -= 1
            elif opcode == 0x0C:
                self.INC(operands[0])
            elif opcode == 0x0D:
                self.DEC(operands[0])
            elif opcode == 0x0E:
                self.registers["C"] = operands[1].value
            elif opcode == 0x0F:
                a = self.registers["A"]
                val = (a >> 1) + ((a & 1) << 7) + ((a & 1) << 8)
                # Flags
                self.registers.__setitem__("z", 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", val > 0xFF)
                # Set
                val &= 0xFF
                self.registers["A"] = val
            # TODO: STOP
            elif opcode == 0x10:
                pass
            elif opcode == 0x11:
                self.registers["DE"] = operands[1].value
            elif opcode == 0x12:
                ptr = self.registers["DE"]
                self.decoder.setMem(ptr, self.registers["A"])
            elif opcode == 0x13:
                self.registers["DE"] += 1
            elif opcode == 0x14:
                self.INC(operands[0])
            elif opcode == 0x15:
                self.DEC(operands[0])
            elif opcode == 0x16:
                self.registers["D"] = operands[1].value
            elif opcode == 0x17:
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
            elif opcode == 0x18:
                self.registers["PC"] += ((operands[0].value ^ 0x80) - 0x80)
            elif opcode == 0x19:
                val = self.registers["HL"]
                res = self.registers["DE"]
                # flags
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xFFF) + (res & 0xFFF) > 0xFFF)
                self.registers.__setitem__("c", val + res > 0xFFFF)
                # Set register value
                self.registers["HL"] = val + res
            elif opcode == 0x1A:
                ptr = self.registers["DE"]
                self.registers["A"] = self.decoder.getMem(ptr)
            elif opcode == 0x1B:
                self.registers["DE"] -= 1
            elif opcode == 0x1C:
                self.INC(operands[0])
            elif opcode == 0x1D:
                self.DEC(operands[0])
            elif opcode == 0x1E:
                self.registers["E"] = operands[1].value
            elif opcode == 0x1F:
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
            elif opcode == 0x20:
                z = self.registers["z"]
                if z == 0:
                    self.JR(operands[1])
                else:
                    return instruction.cycles[1]
            elif opcode == 0x21:
                self.registers["HL"] = operands[1].value
            elif opcode == 0x22:
                ptr = self.registers["HL"]
                self.decoder.setMem(ptr, self.registers["A"])
                self.registers["HL"] += 1
            elif opcode == 0x23:
                self.registers["HL"] += 1
            elif opcode == 0x24:
                self.INC(operands[0])
            elif opcode == 0x25:
                self.DEC(operands[0])
            elif opcode == 0x26:
                self.registers["H"] = operands[1].value
            elif opcode == 0x27:
                t = self.registers["A"]
                corr = 0
                corr |= 0x06 if self.registers["h"] else 0x00
                corr |= 0x60 if self.registers["c"] else 0x00
                if self.registers["n"]:
                    t -= corr
                else:
                    corr |= 0x06 if (t & 0x0F) > 0x09 else 0x00
                    corr |= 0x60 if t > 0x99 else 0x00
                    t += corr
                # flags
                self.registers["z"] = (t & 0xFF) == 0
                self.registers["c"] = (corr & 0x60) != 0
                self.registers["h"] = 0
                # set
                self.registers["A"] = t
            elif opcode == 0x28:
                z = self.registers["z"]
                if z:
                    self.JR(operands[1])
                else:
                    return instruction.cycles[1]
            elif opcode == 0x29:
                val = self.registers["HL"]
                res = self.registers["HL"]
                # flags
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xFFF) + (res & 0xFFF) > 0xFFF)
                self.registers.__setitem__("c", val + res > 0xFFFF)
                # Set register value
                self.registers["HL"] = val + res
            elif opcode == 0x2A:
                ptr = self.registers["HL"]
                self.registers["A"] = self.decoder.getMem(ptr)
                self.registers["HL"] += 1
            elif opcode == 0x2B:
                self.registers["HL"] -= 1
            elif opcode == 0x2C:
                self.INC(operands[0])
            elif opcode == 0x2D:
                self.DEC(operands[0])
            elif opcode == 0x2E:
                self.registers["L"] = operands[1].value
            elif opcode == 0x2F:
                self.registers.__setitem__("A", ~self.registers.__getitem__("A"))
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", 1)
            elif opcode == 0x30:
                c = self.registers["c"]
                if c == 0:
                    self.JR(operands[1])
                else:
                    return instruction.cycles[1]
            elif opcode == 0x31:
                self.registers["SP"] = operands[1].value
            elif opcode == 0x32:
                ptr = self.registers["HL"]
                self.decoder.setMem(ptr, self.registers["A"])
                self.registers["HL"] -= 1
            elif opcode == 0x33:
                self.registers["SP"] += 1
            elif opcode == 0x34:
                ptr = self.registers["HL"]
                val = self.decoder.getMem(ptr)
                # flags
                self.registers.__setitem__("z", (val + 1) & 0xFF == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + 1 > 0xF)
                # set
                val += 1
                self.cycles += 4
                self.decoder.setMem(ptr, val)
            elif opcode == 0x35:
                ptr = self.registers["HL"]
                val = self.decoder.getMem(ptr)
                # flags
                self.registers.__setitem__("z", (val - 1) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - 1 < 0)
                # set
                val -= 1
                self.cycles += 4
                self.decoder.setMem(ptr, val)
            elif opcode == 0x36:
                ptr = self.registers["HL"]
                self.cycles += 4
                self.decoder.setMem(ptr, operands[1].value)
            elif opcode == 0x37:
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 1)
            elif opcode == 0x38:
                c = self.registers["c"]
                if c:
                    self.JR(operands[1])
                else:
                    return instruction.cycles[1]
            elif opcode == 0x39:
                val = self.registers["HL"]
                res = self.registers["SP"]
                # flags
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xFFF) + (res & 0xFFF) > 0xFFF)
                self.registers.__setitem__("c", val + res > 0xFFFF)
                # Set register value
                self.registers["HL"] = val + res
            elif opcode == 0x3A:
                ptr = self.registers["HL"]
                self.registers["A"] = self.decoder.getMem(ptr)
                self.registers["HL"] -= 1
            elif opcode == 0x3B:
                self.registers["SP"] -= 1
            elif opcode == 0x3C:
                self.INC(operands[0])
            elif opcode == 0x3D:
                self.DEC(operands[0])
            elif opcode == 0x3E:
                self.registers["A"] = operands[1].value
            elif opcode == 0x3F:
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", not self.registers.__getitem__("c"))
            elif opcode == 0x40:
                self.registers["B"] = self.registers["B"]
            elif opcode == 0x41:
                self.registers["B"] = self.registers["C"]
            elif opcode == 0x42:
                self.registers["B"] = self.registers["D"]
            elif opcode == 0x43:
                self.registers["B"] = self.registers["E"]
            elif opcode == 0x44:
                self.registers["B"] = self.registers["H"]
            elif opcode == 0x45:
                self.registers["B"] = self.registers["L"]
            elif opcode == 0x46:
                ptr = self.registers["HL"]
                self.registers["B"] = self.decoder.getMem(ptr)
            elif opcode == 0x47:
                self.registers["B"] = self.registers["A"]
            elif opcode == 0x48:
                self.registers["C"] = self.registers["B"]
            elif opcode == 0x49:
                self.registers["C"] = self.registers["C"]
            elif opcode == 0x4A:
                self.registers["C"] = self.registers["D"]
            elif opcode == 0x4B:
                self.registers["C"] = self.registers["E"]
            elif opcode == 0x4C:
                self.registers["C"] = self.registers["H"]
            elif opcode == 0x4D:
                self.registers["C"] = self.registers["L"]
            elif opcode == 0x4E:
                ptr = self.registers["HL"]
                self.registers["C"] = self.decoder.getMem(ptr)
            elif opcode == 0x4F:
                self.registers["C"] = self.registers["A"]
            elif opcode == 0x50:
                self.registers["D"] = self.registers["B"]
            elif opcode == 0x51:
                self.registers["D"] = self.registers["C"]
            elif opcode == 0x52:
                self.registers["D"] = self.registers["D"]
            elif opcode == 0x53:
                self.registers["D"] = self.registers["E"]
            elif opcode == 0x54:
                self.registers["D"] = self.registers["H"]
            elif opcode == 0x55:
                self.registers["D"] = self.registers["L"]
            elif opcode == 0x56:
                ptr = self.registers["HL"]
                self.registers["D"] = self.decoder.getMem(ptr)
            elif opcode == 0x57:
                self.registers["D"] = self.registers["A"]
            elif opcode == 0x58:
                self.registers["E"] = self.registers["B"]
            elif opcode == 0x59:
                self.registers["E"] = self.registers["C"]
            elif opcode == 0x5A:
                self.registers["E"] = self.registers["D"]
            elif opcode == 0x5B:
                self.registers["E"] = self.registers["E"]
            elif opcode == 0x5C:
                self.registers["E"] = self.registers["H"]
            elif opcode == 0x5D:
                self.registers["E"] = self.registers["L"]
            elif opcode == 0x5E:
                ptr = self.registers["HL"]
                self.registers["E"] = self.decoder.getMem(ptr)
            elif opcode == 0x5F:
                self.registers["E"] = self.registers["A"]
            elif opcode == 0x60:
                self.registers["H"] = self.registers["B"]
            elif opcode == 0x61:
                self.registers["H"] = self.registers["C"]
            elif opcode == 0x62:
                self.registers["H"] = self.registers["D"]
            elif opcode == 0x63:
                self.registers["H"] = self.registers["E"]
            elif opcode == 0x64:
                self.registers["H"] = self.registers["H"]
            elif opcode == 0x65:
                self.registers["H"] = self.registers["L"]
            elif opcode == 0x66:
                ptr = self.registers["HL"]
                self.registers["H"] = self.decoder.getMem(ptr)
            elif opcode == 0x67:
                self.registers["H"] = self.registers["A"]
            elif opcode == 0x68:
                self.registers["L"] = self.registers["B"]
            elif opcode == 0x69:
                self.registers["L"] = self.registers["C"]
            elif opcode == 0x6A:
                self.registers["L"] = self.registers["D"]
            elif opcode == 0x6B:
                self.registers["L"] = self.registers["E"]
            elif opcode == 0x6C:
                self.registers["L"] = self.registers["H"]
            elif opcode == 0x6D:
                self.registers["L"] = self.registers["L"]
            elif opcode == 0x6E:
                ptr = self.registers["HL"]
                self.registers["L"] = self.decoder.getMem(ptr)
            elif opcode == 0x6F:
                self.registers["L"] = self.registers["A"]
            elif opcode == 0x70:
                self.decoder.setMem(self.registers["HL"], self.registers["B"])
            elif opcode == 0x71:
                self.decoder.setMem(self.registers["HL"], self.registers["C"])
            elif opcode == 0x72:
                self.decoder.setMem(self.registers["HL"], self.registers["D"])
            elif opcode == 0x73:
                self.decoder.setMem(self.registers["HL"], self.registers["E"])
            elif opcode == 0x74:
                self.decoder.setMem(self.registers["HL"], self.registers["H"])
            elif opcode == 0x75:
                self.decoder.setMem(self.registers["HL"], self.registers["L"])
            elif opcode == 0x76:
                self.halt = True
            elif opcode == 0x77:
                self.decoder.setMem(self.registers["HL"], self.registers["A"])
            elif opcode == 0x78:
                self.registers["A"] = self.registers["B"]
            elif opcode == 0x79:
                self.registers["A"] = self.registers["C"]
            elif opcode == 0x7A:
                self.registers["A"] = self.registers["D"]
            elif opcode == 0x7B:
                self.registers["A"] = self.registers["E"]
            elif opcode == 0x7C:
                self.registers["A"] = self.registers["H"]
            elif opcode == 0x7D:
                self.registers["A"] = self.registers["L"]
            elif opcode == 0x7E:
                ptr = self.registers["HL"]
                self.registers["A"] = self.decoder.getMem(ptr)
            elif opcode == 0x7F:
                self.registers["A"] = self.registers["A"]
            elif opcode == 0x80:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x81:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x82:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x83:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x84:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x85:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x86:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                # flags
                self.registers["z"] = ((val + res) & 0xFF) == 0
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                self.registers.__setitem__("c", val + res > 0xFF)
                # Set register value
                self.registers["A"] = val + res
            elif opcode == 0x87:
                self.ADD(operands[0], operands[1])
            elif opcode == 0x88:
                self.ADC(operands[1])
            elif opcode == 0x89:
                self.ADC(operands[1])
            elif opcode == 0x8A:
                self.ADC(operands[1])
            elif opcode == 0x8B:
                self.ADC(operands[1])
            elif opcode == 0x8C:
                self.ADC(operands[1])
            elif opcode == 0x8D:
                self.ADC(operands[1])
            elif opcode == 0x8E:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                carry = self.registers["c"]
                # flags
                self.registers["z"] = (val + res + carry) & 0xFF == 0
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) + carry > 0xF)
                self.registers.__setitem__("c", val + res + carry > 0xFF)
                # Set register value
                self.registers["A"] = val + res + carry
            elif opcode == 0x8F:
                self.ADC(operands[1])
            elif opcode == 0x90:
                self.SUB(operands[0])
            elif opcode == 0x91:
                self.SUB(operands[0])
            elif opcode == 0x92:
                self.SUB(operands[0])
            elif opcode == 0x93:
                self.SUB(operands[0])
            elif opcode == 0x94:
                self.SUB(operands[0])
            elif opcode == 0x95:
                self.SUB(operands[0])
            elif opcode == 0x96:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                # Flags
                self.registers.__setitem__("z", (val - res) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) < 0)
                # set
                self.registers["A"] = val - res
            elif opcode == 0x97:
                self.SUB(operands[0])
            elif opcode == 0x98:
                self.SBC(operands[1])
            elif opcode == 0x99:
                self.SBC(operands[1])
            elif opcode == 0x9A:
                self.SBC(operands[1])
            elif opcode == 0x9B:
                self.SBC(operands[1])
            elif opcode == 0x9C:
                self.SBC(operands[1])
            elif opcode == 0x9D:
                self.SBC(operands[1])
            elif opcode == 0x9E:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                carry = self.registers.__getitem__("c")
                # Flags
                self.registers.__setitem__("z", (val - res - carry) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) - carry < 0)
                self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) - (carry & 0xFF) < 0)
                # set
                self.registers["A"] = val - res - carry
            elif opcode == 0x9F:
                self.SBC(operands[1])
            elif opcode == 0xA0:
                self.AND(operands[0])
            elif opcode == 0xA1:
                self.AND(operands[0])
            elif opcode == 0xA2:
                self.AND(operands[0])
            elif opcode == 0xA3:
                self.AND(operands[0])
            elif opcode == 0xA4:
                self.AND(operands[0])
            elif opcode == 0xA5:
                self.AND(operands[0])
            elif opcode == 0xA6:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                self.registers["A"] = val & res

                # Flags
                self.registers.__setitem__("z", (val & res) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 1)
                self.registers.__setitem__("c", 0)
            elif opcode == 0xA7:
                self.AND(operands[0])
            elif opcode == 0xA8:
                self.XOR(operands[0])
            elif opcode == 0xA9:
                self.XOR(operands[0])
            elif opcode == 0xAA:
                self.XOR(operands[0])
            elif opcode == 0xAB:
                self.XOR(operands[0])
            elif opcode == 0xAC:
                self.XOR(operands[0])
            elif opcode == 0xAD:
                self.XOR(operands[0])
            elif opcode == 0xAE:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                self.registers["A"] = val ^ res

                # Flags
                self.registers.__setitem__("z", ((val ^ res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)
            elif opcode == 0xAF:
                self.XOR(operands[0])
            elif opcode == 0xB0:
                self.OR(operands[0])
            elif opcode == 0xB1:
                self.OR(operands[0])
            elif opcode == 0xB2:
                self.OR(operands[0])
            elif opcode == 0xB3:
                self.OR(operands[0])
            elif opcode == 0xB4:
                self.OR(operands[0])
            elif opcode == 0xB5:
                self.OR(operands[0])
            elif opcode == 0xB6:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                self.registers["A"] = val | res

                # Flags
                self.registers.__setitem__("z", ((val | res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)
            elif opcode == 0xB7:
                self.OR(operands[0])
            elif opcode == 0xB8:
                self.CP(operands[0])
            elif opcode == 0xB9:
                self.CP(operands[0])
            elif opcode == 0xBA:
                self.CP(operands[0])
            elif opcode == 0xBB:
                self.CP(operands[0])
            elif opcode == 0xBC:
                self.CP(operands[0])
            elif opcode == 0xBD:
                self.CP(operands[0])
            elif opcode == 0xBE:
                val = self.registers["A"]
                res = self.decoder.getMem(self.registers["HL"])
                # Flags
                self.registers.__setitem__("z", val == res)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", val < res)
            elif opcode == 0xBF:
                self.CP(operands[0])
            elif opcode == 0xC0:
                if self.registers["z"] == 0:
                    self.RET()
                else:
                    return instruction.cycles[1]
            elif opcode == 0xC1:
                self.POP(operands[0])
            elif opcode == 0xC2:
                if self.registers["z"] == 0:
                    self.JP(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xC3:
                self.JP(operands[0].value)
            elif opcode == 0xC4:
                if self.registers["z"] == 0:
                    self.CALL(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xC5:
                self.PUSH(operands[0])
            elif opcode == 0xC6:
                val = self.registers["A"]
                res = operands[1].value
                # flags
                self.registers["z"] = ((val + res) & 0xFF) == 0
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                self.registers.__setitem__("c", val + res > 0xFF)
                # Set register value
                self.registers["A"] = val + res
            elif opcode == 0xC7:
                self.CALL(0x0)
            elif opcode == 0xC8:
                if self.registers["z"]:
                    self.RET()
                else:
                    return instruction.cycles[1]
            elif opcode == 0xC9:
                self.RET()
            elif opcode == 0xCA:
                if self.registers["z"]:
                    self.JP(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xCB:
                raise InstructionError(f"Instruction {instruction} is illegal")
            elif opcode == 0xCC:
                if self.registers["z"]:
                    self.CALL(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xCD:
                self.CALL(operands[0].value)
            elif opcode == 0xCE:
                val = self.registers["A"]
                res = operands[1].value
                carry = self.registers["c"]
                # flags
                self.registers["z"] = (val + res + carry) & 0xFF == 0
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) + carry > 0xF)
                self.registers.__setitem__("c", val + res + carry > 0xFF)
                # Set register value
                self.registers["A"] = val + res + carry
            elif opcode == 0xCF:
                self.CALL(0x8)
            elif opcode == 0xD0:
                if self.registers["c"] == 0:
                    self.RET()
                else:
                    return instruction.cycles[1]
            elif opcode == 0xD1:
                self.POP(operands[0])
            elif opcode == 0xD2:
                if self.registers["c"] == 0:
                    self.JP(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xD4:
                if self.registers["c"] == 0:
                    self.CALL(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xD5:
                self.PUSH(operands[0])
            elif opcode == 0xD6:
                val = self.registers["A"]
                res = operands[0].value
                # Flags
                self.registers.__setitem__("z", (val - res) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) < 0)
                # set
                self.registers["A"] = val - res
            elif opcode == 0xD7:
                self.CALL(0x10)
            elif opcode == 0xD8:
                if self.registers["c"]:
                    self.RET()
                else:
                    return instruction.cycles[1]
            elif opcode == 0xD9:
                self.i_master = True
                self.RET()
            elif opcode == 0xDA:
                if self.registers["c"]:
                    self.JP(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xDC:
                if self.registers["c"]:
                    self.CALL(operands[1].value)
                else:
                    return instruction.cycles[1]
            elif opcode == 0xDE:
                val = self.registers["A"]
                res = operands[1].value
                carry = self.registers.__getitem__("c")
                # Flags
                self.registers.__setitem__("z", (val - res - carry) & 0xFF == 0)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) - carry < 0)
                self.registers.__setitem__("c", (val & 0xFF) - (res & 0xFF) - (carry & 0xFF) < 0)
                # set
                self.registers["A"] = val - res - carry
            elif opcode == 0xDF:
                self.CALL(0x18)
            elif opcode == 0xE0:
                # (a8)
                ptr = operands[0].value
                a = self.registers["A"]
                # (a8 + 0xFF00) = A
                self.cycles += 4
                self.decoder.setMem(ptr + 0xFF00, a)
            elif opcode == 0xE1:
                self.POP(operands[0])
            elif opcode == 0xE2:
                # (C)
                ptr = self.registers["C"]
                a = self.registers["A"]
                # (C + 0xFF00) = A
                self.decoder.setMem(ptr + 0xFF00, a)
            elif opcode == 0xE5:
                self.PUSH(operands[0])
            elif opcode == 0xE6:
                val = self.registers["A"]
                res = operands[0].value
                self.registers["A"] = val & res

                # Flags
                self.registers.__setitem__("z", (val & res) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 1)
                self.registers.__setitem__("c", 0)
            elif opcode == 0xE7:
                self.CALL(0x20)
            elif opcode == 0xE8:
                val = self.registers["SP"]
                res = operands[1].value
                # flags
                self.registers["z"] = 0
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) > 0xFF)
                # Set register value
                self.registers["SP"] = val + ((res ^ 0x80) - 0x80)
            elif opcode == 0xE9:
                self.registers["PC"] = self.registers["HL"]
            elif opcode == 0xEA:
                self.cycles += 8
                self.decoder.setMem(operands[0].value, self.registers["A"])
            elif opcode == 0xEE:
                val = self.registers["A"]
                res = operands[0].value
                self.registers["A"] = val ^ res

                # Flags
                self.registers.__setitem__("z", ((val ^ res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)
            elif opcode == 0xEF:
                self.CALL(0x28)
            elif opcode == 0xF0:
                # (a8)
                ptr = operands[1].value
                self.cycles += 4
                item = self.decoder.getMem(ptr + 0xFF00)
                # A = (a8 + ff00)
                self.registers["A"] = item
            elif opcode == 0xF1:
                val = self.decoder.getMem(self.registers["SP"])
                res = self.decoder.getMem(self.registers["SP"] + 1)
                self.registers["SP"] += 2
                self.registers["A"] = res
                self.registers["F"] = val & 0xF0 & 0xF0

            elif opcode == 0xF2:
                # (C)
                ptr = self.registers["C"]
                item = self.decoder.getMem(ptr + 0xFF00)
                # A = (C + 0xFF00)
                self.registers["A"] = item
            elif opcode == 0xF3:
                self.i_master = 0
            elif opcode == 0xF5:
                self.decoder.setMem(self.registers["SP"] - 1, self.registers["A"])
                self.decoder.setMem(self.registers["SP"] - 2, self.registers["F"] & 0xF0)
                self.registers["SP"] -= 2
            elif opcode == 0xF6:
                val = self.registers["A"]
                res = operands[0].value
                self.registers["A"] = val | res

                # Flags
                self.registers.__setitem__("z", ((val | res) & 0xFF) == 0)
                self.registers.__setitem__("n", 0)
                self.registers.__setitem__("h", 0)
                self.registers.__setitem__("c", 0)
            elif opcode == 0xF7:
                self.CALL(0x30)
            elif opcode == 0xF8:
                res = operands[2].value
                val = self.registers["SP"]
                # HL = SP + r8
                self.registers["HL"] = val + ((res ^ 0x80) - 0x80)
                # Flags
                self.registers["z"] = 0
                self.registers["n"] = 0
                self.registers.__setitem__("h", (val & 0xF) + (res & 0xF) > 0xF)
                self.registers.__setitem__("c", (val & 0xFF) + (res & 0xFF) > 0xFF)
            elif opcode == 0xF9:
                self.registers["SP"] = self.registers["HL"]
            elif opcode == 0xFA:
                self.cycles += 8
                self.registers["A"] = self.decoder.getMem(operands[1].value)
            elif opcode == 0xFB:
                self.i_master = 1
            elif opcode == 0xFE:
                val = self.registers["A"]
                res = operands[0].value
                # Flags
                self.registers.__setitem__("z", val == res)
                self.registers.__setitem__("n", 1)
                self.registers.__setitem__("h", (val & 0xF) - (res & 0xF) < 0)
                self.registers.__setitem__("c", val < res)
            elif opcode == 0xFF:
                self.CALL(0x38)
            else:
                raise InstructionError(f"Unimplemented instruction: {instruction}")

        return instruction.cycles[0]

    def run(self):
        counter = 0
        while True:
            # if counter == 10000:
            # self.generateLog(f)
            # self.registers.print()
            # counter = 0
            self.update()
            # counter += 1
    def generateLog(self, file):
        a = self.registers["A"]
        f = self.registers["F"]
        b = self.registers["B"]
        c = self.registers["C"]
        d = self.registers["D"]
        e = self.registers["E"]
        h = self.registers["H"]
        l = self.registers["L"]
        sp = self.registers["SP"]
        pc = self.registers["PC"]
        mem1 = self.decoder.getMem(pc)
        mem2 = self.decoder.getMem(pc + 1)
        mem3 = self.decoder.getMem(pc + 2)
        mem4 = self.decoder.getMem(pc + 3)
        file.write(f"A:{a:02x} F:{f:02x} B:{b:02x} C:{c:02x} D:{d:02x} E:{e:02x} H:{h:02x} L:{l:02x} SP:{sp:04x} PC:{pc:04x} PCMEM:{mem1:02x},{mem2:02x},{mem3:02x},{mem4:02x}\n")

    def handleEvents(self):
        for event in pygame.event.get():
            # Handle quit
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            interrupt = False
            if event.type == pygame.KEYUP:
                updog = True
                # dpad up
                if event.key == pygame.K_w:
                    interrupt = self.joypad.handleInput(2, updog)
                # dpad down
                elif event.key == pygame.K_s:
                    interrupt = self.joypad.handleInput(3, updog)
                # dpad left
                elif event.key == pygame.K_a:
                    interrupt = self.joypad.handleInput(1, updog)
                # dpad right
                elif event.key == pygame.K_d:
                    interrupt = self.joypad.handleInput(0, updog)


                # Select
                elif event.key == pygame.K_k:
                    interrupt = self.joypad.handleInput(6, updog)
                # Start
                elif event.key == pygame.K_l:
                    interrupt = self.joypad.handleInput(7, updog)
                # A
                elif event.key == pygame.K_o:
                    interrupt = self.joypad.handleInput(4, updog)
                # B
                elif event.key == pygame.K_p:
                    interrupt = self.joypad.handleInput(5, updog)

            elif event.type == pygame.KEYDOWN:
                updog = False
                # Joypad up
                if event.key == pygame.K_w:
                    interrupt = self.joypad.handleInput(2, updog)
                # Joypad down
                elif event.key == pygame.K_s:
                    interrupt = self.joypad.handleInput(3, updog)
                # Joypad left
                elif event.key == pygame.K_a:
                    interrupt = self.joypad.handleInput(1, updog)
                # Joypad right
                elif event.key == pygame.K_d:
                    interrupt = self.joypad.handleInput(0, updog)

                # Select
                elif event.key == pygame.K_k:
                    interrupt = self.joypad.handleInput(6, updog)
                # Start
                elif event.key == pygame.K_l:
                    interrupt = self.joypad.handleInput(7, updog)
                # A
                elif event.key == pygame.K_o:
                    interrupt = self.joypad.handleInput(4, updog)
                # B
                elif event.key == pygame.K_p:
                    interrupt = self.joypad.handleInput(5, updog)

            # Set joypad interrupt
            if interrupt:
                self.setInterrupt(4)

    def update(self):
        # blargg debug
        # self.blargg_update()

        # handle events
        self.handleEvents()
        # execute
        if not self.halt:
            cycles = self.executeNextOp()
        else:
            cycles = 4

        # tick timer
        timer_inter = self.timer.tick(cycles - self.sync_cycles)
        if timer_inter:
            self.setInterrupt(2)

        # update graphics
        self.screen.update(cycles - self.sync_cycles)

        # reset sync
        self.sync_cycles = 0
        self.cycles = 0

        # check interrupts
        if self.checkInterrupt():
            self.halt = False

        # halt
        if self.halt and self.i_queue:
            self.halt = False
            self.registers["PC"] += 1

        self.i_queue = False

    def executeNextOp(self):
        address = self.registers["PC"]
        try:
            wrapper = self.decoder.decode(address)
            next_address, instruction, cb = wrapper.address, wrapper.instruction, wrapper.cbbool
        except IndexError:
            raise InstructionError(f"Cannot execute on {address}")
        self.registers["PC"] = next_address
        cycles = self.execute(instruction, cb)
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

            self.i_queue = True
            return True
        else:
            self.i_queue = False
            return False

    def handleInterrupt(self, flag, address):
        self.i_flag ^= flag  # remove flag

        self.decoder.setMem((self.registers["SP"] - 1) & 0xFFFF, self.registers["PC"] >> 8)
        self.decoder.setMem((self.registers["SP"] - 2) & 0xFFFF, self.registers["PC"] & 0xFF)
        self.registers["SP"] -= 2

        self.registers["PC"] = address
        self.i_master = False

    def blargg_update(self):
        temp = False
        if self.decoder.getMem(0xFF02) == 0x81:
            val = chr(int(self.decoder.getMem(0xFF01)))
            self.blargg += val
            self.decoder.setMem(0xFF02, 0)
            temp = True

        if self.blargg and temp:
            print(self.blargg)

