from cartridge import get_cartridge_metadata
import cpu
from pathlib import Path
import pygame

# filename = '../test roms/blargg tests/mem_timing/mem_timing.gb'
# filename = '../test roms/blargg tests/cpu_instrs/cpu_instrs.gb'
# filename = '../test roms/blargg tests/instr_timing/instr_timing.gb'
# filename = '../test roms/blargg tests/mem_timing-2/mem_timing.gb'
# filename = "../test roms/mooneye/emulator-only/mbc1/rom_512kb.gb"
# filename = "../test roms/age-test-roms/vram/vram-read-dmgC.gb"
# filename = "../test roms/dmg-acid2.gb"

# BREAKPOINT 0x297
filename = "../test roms/kirby.gb"

metadata = get_cartridge_metadata(filename)
print(metadata)
cpu = cpu.CPU(filename, metadata)
cpu.initVals()
cpu.run()

# from pyboy import PyBoy
# pyboy = PyBoy(filename)
# while pyboy.tick():
#     pass
# pyboy.stop()




