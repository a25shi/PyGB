from cartridge import get_cartridge_metadata
from cpu import CPU

# BREAKPOINT 0x297
filename = "../test roms/super mario.gb"

metadata = get_cartridge_metadata(filename)
cpu = CPU(filename, metadata)
cpu.initVals()
cpu.run()





