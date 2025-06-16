# Registers
# cython: annotation_typing = False
# from collections.abc import MutableMapping
from dataclasses import dataclass
import cython


# Constants
REGISTERS_LOW = {"F": "AF", "C": "BC", "E": "DE", "L": "HL"}
REGISTERS_HIGH = {"A": "AF", "B": "BC", "D": "DE", "H": "HL"}
REGISTERS = {"AF", "BC", "DE", "HL", "PC", "SP"}
FLAGS = {"c": 4, "h": 5, "n": 6, "z": 7}

@dataclass
@cython.cclass
class Registers:
    AF: cython.int
    BC: cython.int
    DE: cython.int
    HL: cython.int
    PC: cython.int
    SP: cython.int

    # def values(self):
    #     return [self.AF, self.BC, self.DE, self.HL, self.PC, self.SP]
    #
    # def __iter__(self):
    #     return iter(self.values())
    #
    # def __len__(self):
    #     return len(self.values())

    @cython.cfunc
    def print(self):
        print(
            f"AF: {hex(self.AF)} BC: {hex(self.BC)} DE: {hex(self.DE)} HL: {hex(self.HL)} PC: {hex(self.PC)} SP: {hex(self.SP)}")

    def __setitem__(self, key: str, value: int):
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

    def __delitem__(self, key: str):
        raise NotImplementedError("Register deletion is not supported")

    def __getitem__(self, key: str):
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