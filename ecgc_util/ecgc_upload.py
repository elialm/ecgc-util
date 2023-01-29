from .ecgc_spi_programmer import SpiProgrammer

def main_cli():
    programmer = SpiProgrammer('COM4')
    programmer.enable()
    programmer.write(b'hello there general kenobi')
    programmer.disable()

if __name__ == '__main__':
    main_cli()