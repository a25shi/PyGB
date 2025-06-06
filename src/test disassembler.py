from cartridge import get_cartridge_metadata
import cpu
from pathlib import Path
def init(cpu_):
    cpu_.registers.__setitem__("AF", 0x01B0)
    cpu_.registers.__setitem__("BC", 0x0013)
    cpu_.registers.__setitem__("DE", 0x00D8)
    cpu_.registers.__setitem__("HL", 0x014D)
    cpu_.registers.__setitem__("SP", 0xFFFE)
    cpu_.registers.__setitem__("PC", 0x0100)
    cpu_.decoder.set(0xFF05, 0x00)
    cpu_.decoder.set(0xFF06, 0x00)
    cpu_.decoder.set(0xFF07, 0x00)
    cpu_.decoder.set(0xFF10, 0x80)
    cpu_.decoder.set(0xFF11, 0xBF)
    cpu_.decoder.set(0xFF12, 0xF3)
    cpu_.decoder.set(0xFF14, 0xBF)
    cpu_.decoder.set(0xFF16, 0x3F)
    cpu_.decoder.set(0xFF17, 0x00)
    cpu_.decoder.set(0xFF19, 0xBF)
    cpu_.decoder.set(0xFF1A, 0x7F)
    cpu_.decoder.set(0xFF1B, 0xFF)
    cpu_.decoder.set(0xFF1C, 0x9F)
    cpu_.decoder.set(0xFF1E, 0xBF)
    cpu_.decoder.set(0xFF20, 0xFF)
    cpu_.decoder.set(0xFF21, 0x00)
    cpu_.decoder.set(0xFF22, 0x00)
    cpu_.decoder.set(0xFF23, 0xBF)
    cpu_.decoder.set(0xFF24, 0x77)
    cpu_.decoder.set(0xFF25, 0xF3)
    cpu_.decoder.set(0xFF26, 0xF1)
    cpu_.decoder.set(0xFF40, 0x91)
    cpu_.decoder.set(0xFF42, 0x00)
    cpu_.decoder.set(0xFF43, 0x00)
    cpu_.decoder.set(0xFF45, 0x00)
    cpu_.decoder.set(0xFF47, 0xFC)
    cpu_.decoder.set(0xFF48, 0xFF)
    cpu_.decoder.set(0xFF48, 0xFF)
    cpu_.decoder.set(0xFF49, 0xFF)
    cpu_.decoder.set(0xFF4A, 0x00)
    cpu_.decoder.set(0xFF4B, 0x00)
    cpu_.decoder.set(0xFFFF, 0x00)

# filename = '../test roms/blargg tests/mem_timing/mem_timing.gb'
filename = '../test roms/blargg tests/cpu_instrs/cpu_instrs.gb'
# filename = '../test roms/blargg tests/instr_timing/instr_timing.gb'
# filename = "../test roms/mooneye/acceptance/bits/reg_f.gb"
# filename = "../test roms/super mario.gb"
metadata = get_cartridge_metadata(filename)
print(metadata)
cpu = cpu.CPU(filename, metadata)
init(cpu)
cpu.run()






