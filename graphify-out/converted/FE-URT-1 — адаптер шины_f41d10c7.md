<!-- converted from FE-URT-1 — адаптер шины.xlsx -->

## Sheet: FE-URT-1
| FE-URT-1 USB to TTL, 485 bus programmer |
| --- |
| SKU：FE-URT1-C001 |
| The Size：52*38.4*16mm |
| The Power supply Voltage： 4.8-25V |
| The Baud Rate：50bps-1Mbps |
| The USB interface：Micro USB |
| The UART connector：2.54 Pitch pin  |
| FE-URT-1 USE MANUAL |
| Multi function serial port signal converter《USB/URAT TO SMS（RS485）&SCS(TTL)》  |
| 1. Overview of 1. functions |
| URT-1 multifunction serial signal converter, in order to facilitate the user to debug and use SMS and SCS composite Feite series serial servo design. |
| URT-1 integrated USB serial port chip, combined with linear low-voltage differential voltage regulator circuit, USB signal can be easily converted to 5V or 3V3 serial signal level. |
| In the URT-1 board, serial signal conversion circuit respectively into two different levels of signal, which A road - asynchronous half duplex RS485 level port can be connected to the SMS series servo; B - asynchronous half duplex TTL level single bus port can be connected to the SCS series of steering gear. |
| In the URT-1 board in the input and output signal by using asynchronous serial time-sharing using hardware circuit, hardware automatic diversion, without the use of additional IO enable to control, reduce the occupation of MCU port burden and code simple. |
| USB port using USB MINI interface; UART interface with 2.54 row spacing general; SMS series servo interface using 5264-4AW interface can be directly connected to the steering gear; SCS series servo interface using 5264-3AW interface can be directly connected to the steering gear. |
| The working voltage of SMS and SCS series servo fit is not the same, reuse requires a different working voltage, power supply port and can also access the SCS from the SMS section of the step-down power supply high voltage after making the system with a power supply to provide power. |
| Because the power port has overcurrent limit, the maximum is 6A, so it is necessary to do additional power distribution processing in the actual application of the serial connection of more servos. URT-1 is only used for signal conversion. |
| 2. functional features |
| Full speed USB device interface, compatible with USB V2.0 |
| Support baud rate 50bps~1Mbps |
| 5V and 3V3 UART serial port signal level can be switched freely |
| Supports 32/64 bit Windows 10/8.1/8/7/VISTA/XP, SERVER 2016/2012/2008/20032000/ME/98 |
| Microsoft digital signature authentication |
| SMS and SCS series servos can be shared by one serial port for control |
| The serial port signal is asynchronous half duplex communication mode, and the hardware automatic diversion needs no additional enable IO |
| The interface of servo system adopts error proofing connection to ensure proper connection |
| UART interface is general pin way, can be used as USB to serial port output, also can connect MCU UART to control the steering gear |
| With signal level power indicator (D1), TX (D2) and RX (D3) indicator, convenient to view data status |
| The 5V voltage is supplied from the USB, otherwise the external voltage is supplied to the 5V |
| 500mA overcurrent protection and overvoltage protection for USB power supply belt |
| 3. specification parameters |
| Weight: 12.5 grams |
| Size (L*W*H):55.8 * 36.6 * 11.5 mm |
| Mounting size: 48.8 * 28.8 mm |
| USB interface: MINI USB |
| UART interface: 2.54 pin spacing |
| SCS servo interface: 3PIN 5264-3AW |
| SMS servo interface: 4PIN 5264-4AW |
| Actuator power interface: 5.08 terminal |
| 4.motherboard port: |
| 5. need matching list |
| MINI USB connection line |
| Power supply and line of rudder |
| Connecting line between steering gear and steering engine |
| Du Bangxian (optional) |
| 6. drive installation |
| CH340C driver download address: |
| Http://www.wch.cn/download/CH341SER_EXE.html |
| Run the installer driver after download |
| Click Install to wait for a period of time, do not close the installer before prompt for successful installation. |
| Successfully installed or installed successfully before the driver, in the URT-1 connection to the computer USB port, in the computer device manager can see the corresponding port number. |
| 7. hardware connection |
| Access the corresponding servos to the corresponding servos interface |
| The correct power supply is connected to the servo power supply port, in particular, the positive and negative pole of the power supply can not be connected |
| Connecting URT-1 and PC with MINI USB line |
| The following is a physical connection between the SMS series and the SCS series servos, as shown below: |
| 8. software testing |
| Test with FD software |
| Debugging assistant test with serial port |