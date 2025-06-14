from cartridge import get_cartridge_metadata
from cpu import CPU
import sys
import os
if len(sys.argv) > 2:
    raise AssertionError(f"Only path to rom argument is allowed")

if len(sys.argv) == 1:
    filename = "../test roms/super mario.gb"
else:
    filename = sys.argv[1]

if not os.path.isfile(filename):
    raise AssertionError(f"Rom path {filename} does not exist")

metadata = get_cartridge_metadata(filename)
cpu = CPU(filename, metadata)
cpu.initVals()
cpu.run()



