# ecgc-util

Utility tools for development with the [ecgc Gameboy cartridge](https://efacdev.nl/pages/project/?name=ecgc).
Note that this utility is only compatible with the Gen4 cartridge.

This python repository contains several scripts for ease of development.
The tools released under this repository are:

- **ecgc-upload**
    - For uploading an image file to the cartridge.
    Useful for uploading a boot image or for flashing DRAM.
- **ecgc-dump**
    - For dumping a memory mapped area of cartridge memory.
    Useful for debugging and testing purposes.
- **ecgc-debug**
    - For peeking and poking at memory registers.
    It opens a command prompt where the user can perform these operations.
    Useful for debugging and testing purposes.

For usage information, call the tool with the `-h/--help` flag.

## Building

The project can be built into wheels which can be installed on the user's system.
The the following to build the project into a wheel:

```bash
python -m build
```

The build products can then be found in the created `dist` directory.

## Installing

Installing can be done directly from source of with the builded wheels.
To install directly, run the following (assuming that the current directory is the repo root):

```bash
python -m pip install .
``` 

The wheel can be installed with the following:

```bash
python -m pip install /path/to/wheel.whl
``` 

After installing, the scripts should be available in your PATH.
If not, restart your console and try again.

## Running tests

Inside the project, there are automated tests.
These can be found inside the `tests` directory.
The tests can be run using the `unittest.TestLoader.discover()` method.
To invoke this via the console, use the following command:

```bash
python -m unittest discover tests "*_test.py"
```

This should run all tests and give the appropriate test results.
