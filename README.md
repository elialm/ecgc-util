# ecgc-util

Utility tools for development with the [ecgc Gameboy cartridge](https://efacdev.nl/pages/project/?name=ecgc).
This python repository contains several scripts for ease of development.
The tools released under this repository are:

- **ecgc-upload**
    - For uploading an image file to the cartridge. Useful for uploading a boot
    image or for flashing DRAM.
    The utility works in conjunction with the [ecgc SPI programmer](https://github.com/elialm/ecgc-spi-programmer)
    to communicate with the cartridge.
    The utility was developed for the programmer's [v1.0.0a](https://github.com/elialm/ecgc-spi-programmer/releases/tag/v1.0.0a)
    release.

## Usage information

### ecgc-upload

```
usage: ecgc-upload [-h] [-s SIZE] -t {boot,dram,flash} [-v] serial_port image_file

Utility for uploading code to ecgc project cartridge

positional arguments:
  serial_port           Serial port of the spi programmer
  image_file            File to upload to the cartridge

options:
  -h, --help            show this help message and exit
  -s SIZE, --size SIZE  Number for bytes to upload to the cartridge from the image file. If not given, will either upload entire file or fill the given target (if the file is equal of larger than the target)
  -t {boot,dram,flash}, --target {boot,dram,flash}
                        Destination target of the image upload
  -v, --verbose         Increase verbosity of program output
```