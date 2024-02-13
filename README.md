# ecgc-util

Utility tools for development with the [ecgc Gameboy cartridge](https://efacdev.nl/pages/project/?name=ecgc).
This python repository contains several scripts for ease of development.
The tools released under this repository are:

- **ecgc-upload**
    - For uploading an image file to the cartridge. Useful for uploading a boot
    image or for flashing DRAM.
- **ecgc-dump**
    - For dumping a memory mapped area of cartridge memory.
    Useful for debugging and testing purposes.

## Usage information

### ecgc-upload

```
usage: ecgc-upload [-h] [-s SIZE] -t {boot,dram,flash} [-v] serial_port image_file

Utility for uploading code to ecgc project cartridge

positional arguments:
  serial_port           Serial port of the programmer
  image_file            File to upload to the cartridge

options:
  -h, --help            show this help message and exit
  -s SIZE, --size SIZE  Number for bytes to upload to the cartridge from the image file. If not given, will either upload entire file or fill the given target (if the file is equal of larger than the target)
  -t {boot,dram}, --target {boot,dram}
                        Destination target of the image upload
  -v, --verbose         Increase verbosity of program output
```

### ecgc-dump

```
usage: ecgc-dump [-h] -n DUMP_SIZE [-s START_OFFSET] [-v] serial_port output_file

Utility for dumping memory from ecgc project cartridge

positional arguments:
  serial_port      Serial port of the programmer
  output_file      File to output the dump

options:
  -h, --help       show this help message and exit
  -n DUMP_SIZE     Number of bytes to dump
  -s START_OFFSET  Number of bytes to skip from the start
  -v, --verbose    Increase verbosity of program output
```