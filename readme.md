
# PyGB
A functioning **Game Boy** emulator.

Written using Python3, utilizing Cython for performance and PyGame for rendering the display.
## Getting Started

### Installation and Compilation
1. To begin, install the necessary libraries required using `pip` in the base PyGB folder:
   
   `pip install -r requirements.txt`
2. Navigate to the src folder
3. Compile the emulator:
   
   `python ./setup.py build_ext --inplace`

### Usage

1. To run the emulator, use the following command:
   
   `python ./pygb.py path_to_rom`
> Make sure that the rom is placed in the correct path relative to the PyGB/src folder


### PyGB Gameplay
![pygb mario](https://github.com/user-attachments/assets/4efb7c55-0914-4294-9204-58a632b38119)
