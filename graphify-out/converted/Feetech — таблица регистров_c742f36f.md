<!-- converted from Feetech — таблица регистров.xlsx -->

## Sheet: SCS15
|  |  |  | firmware SCServo1.1-STM8-TTL(181129).bin(firmware version：0.5) |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  | No load speed（RPM) |  | 53.7109375 |  | Test voltage(V) |  |  | 7.4 |  |  |
|  |  |  | No load speed（step/s） |  | 1500 |  | No load current（mA) |  |  | 150 |  |  |
|  |  |  | Maximum Effective Angle (Degree) |  | 220 |  |  |  |  |  |  |  |
|  |  |  | Resolution (step) |  | 1024 |  | Support multi turn and large angle control, power failure does not save the number of cycles |  |  |  |  |  |
|  |  |  | Minimum Resolution Angle (Degree/Step) |  | 0.21484375 |  |  |  |  |  |  |  |
|  |  |  | Acceleration (degrees / S ^ 2) |  |  |  |  |  |  |  |  |  |
|  |  | Memory address |  | Function | Bytes | Initial value | Storage area | authority | Minimum value | Maximum value | unit | Analysis of values |
| 0x |  | DEC | HEX |  | High Front Low behind |  |  |  |  |  |  | If the functional address uses two bytes of data, the high byte is at the front address and the low byte is at the back address. |
| 0 |  | 0 | 0x0 | Firmware Main Version Number | 1 | 0 | EPROM | read | 0 | 253 | pcs |  |
| 1 |  | 1 | 0x1 | Firmware sub version number | 1 | 5 | EPROM | read | 0 | 253 | pcs |  |
| 3 |  | 3 | 0x3 | servo Main Version Number | 1 | 5 | EPROM | read | 0 | 253 | pcs |  |
| 4 |  | 4 | 0x4 | servo sub version number | 1 | 15 | EPROM | read&write | 0 | 253 | pcs |  |
| 5 |  | 5 | 0x5 | ID | 1 | 1 | EPROM | read&write | 0 | 253 | pcs | The unique ID number on the bus. No duplicate ID number can appear on the same bus.
No. 254 (OxFE) is the broadcast ID, and the broadcast does not return the reply package. |
| 6 |  | 6 | 0x6 | Baud rate | 1 | 0 | EPROM | read&write | 0 | 7 | number | 0-7 represents the baud rate as follows (factory default is 0)
1000000，500000，250000，128000，115200，76800，57600，38400 |
| 7 |  | 7 | 0x7 | Return delay | 1 | 0 | EPROM | read&write | 0 | 254 | 2us | Minimum unit is 2us, maximum settable return delay 254*2=508us |
| 8 |  | 8 | 0x8 | Response status level | 1 | 1 | EPROM | read&write | 0 | 1 | no | 0: Instructions other than read instructions and PING instructions do not return reply packages
1: Return reply packages for all instructions |
| 9 |  | 9 | 0x9 | Minimum Angle Limitation | 2 | 20 | EPROM | read&write | 0 | 1022 | step | Set the minimum operating angle limit, the value is less than the maximum angle limit, the value is 0 in motor mode. |
| B |  | 11 | 0xB | Maximum Angle Limitation | 2 | 1003 | EPROM | read&write | 0 | 1023 | step | Set the maximum operating angle limit, the value is greater than the minimum angle limit, the value is 0 in motor mode. |
| D |  | 13 | 0xD | Maximum Temperature Limit | 1 | 80 | EPROM | read&write | 0 | 100 | °C | Maximum operating temperature limit, if set to 80, maximum temperature is 80 degrees Celsius, setting accuracy is 1 degrees Celsius. |
| E |  | 14 | 0xE | Maximum input voltage | 1 | 90 | EPROM | read&write | 0 | 254 | 0.1V | If the maximum input voltage is set to 90, the maximum operating voltage is limited to 9.0V and the setting accuracy is 0.1V. |
| F |  | 15 | 0xF | Minimum input voltage | 1 | 45 | EPROM | read&write | 0 | 254 | 0.1V | If the minimum input voltage is set to 50, the minimum working voltage is limited to 5.0V, and the setting accuracy is 0.1V. |
| 10 |  | 16 | 0x10 | Maximum torque | 2 | 1000 | EPROM | read&write | 0 | 1000 | 0.001 | Set the maximum output torque limit of the steering gear and set 1000 = 100%* blocking torque. |
| 12 |  | 18 | 0x12 | phase | 1 | 0 | EPROM | read&write | 0 | 254 | no | Special function bytes, no special requirements can not be modified, see the special byte bit parsing |
| 13 |  | 19 | 0x13 | Unloading condition | 1 | 36 | EPROM | read&write | 0 | 254 | no | Set the corresponding bit 1 to turn on the corresponding protection
Voltage no temperature no overload corresponding position set 0 to turn off corresponding protection |
| 14 |  | 20 | 0x14 | LED Alarm condition | 1 | 37 | EPROM | read&write | 0 | 254 | no | Bit0  Bit1  Bit2 Bit3 Bit4 Bit5 Set the corresponding position 1 to turn on the flash alarm
Voltage no temperature no overload corresponding position set 0 to turn off flash alarm |
| 15 |  | 21 | 0x15 | P Proportionality coefficient | 1 | 15 | EPROM | read&write | 0 | 254 | no | Proportional Coefficient of Control Motor |
| 16 |  | 22 | 0x16 | D Differential coefficient | 1 | 15 | EPROM | read&write | 0 | 254 | no | Differential Coefficient of Control Motor |
| 17 |  | 23 | 0x17 | I Integral coefficient | 1 | 0 | EPROM | read&write | 0 | 254 | no | Integral Coefficient of Control Motor |
| 18 |  | 24 | 0x18 | Minimum startup force | 2 | 30 | EPROM | read&write | 0 | 1000 | 0.001 | Set the minimum output starting torque of the servo, set 1000 = 100%* blocking torque. |
| 1A |  | 26 | 0x1A | Clockwise insensitive area | 1 | 1 | EPROM | read&write | 0 | 32 | step | The minimum unit is a minimum resolution angle. |
| 1B |  | 27 | 0x1B | Counterclockwise insensitive region | 1 | 1 | EPROM | read&write | 0 | 32 | step | The minimum unit is a minimum resolution angle. |
| 1C |  | 28 | 0x1C | Hysteresis loop | 1 | 1 | EPROM | read&write | 0 | 32 | step | The minimum unit is a minimum resolution angle. |
| 25 |  | 37 | 0x25 | Protection torque | 1 | 20 | EPROM | read&write | 0 | 100 | 0.01 | Output torque after entering overload protection, e.g. set 20 to represent 20% maximum torque |
| 26 |  | 38 | 0x26 | Protection time | 1 | 100 | EPROM | read&write | 0 | 254 | 40ms | The current load output exceeds the overload torque and maintains the timing time, such as 100 for 4 seconds, the maximum can be set to 10 seconds. |
| 27 |  | 39 | 0x27 | Overload torque | 1 | 80 | EPROM | read&write | 0 | 100 | 0.01 | Maximum Torque Threshold for Start-up Overload Protection Time Timing, e.g. 80 for 80% Maximum Torque |
| 28 |  | 40 | 0x28 | Torque switch | 1 | 0 | SRAM | read&write | 0 | 3 | no | Write 0: Turn off the torsion output/damping state; Write 1: Turn on the torsion output; Write 2: Write in the free state. |
| 2A |  | 42 | 0x2A | Target location | 2 | 0 | SRAM | read&write | 0 | 1023 | no | Each step is a minimum resolution angle, absolute position control mode, maximum corresponding maximum effective angle. |
| 2C |  | 44 | 0x2C | Running time | 2 | 0 | SRAM | read&write | 0 | 9999 | 1ms | The movement time from the current position to the target position, when the running speed is 0, this parameter takes effect. |
| 2E |  | 46 | 0x2E | running speed | 2 | 0 | SRAM | read&write | 0 | 1000 | step/s | The number of steps to move in unit time (per second) |
| 30 |  | 48 | 0x30 | lock sign | 1 | 1 | SRAM | read&write | 0 | 1 | no | Write 0 closes the write lock, and the value written to the EPROM address is saved after power failure.
Write 1 opens the write lock, and the value written to the EPROM address is power-down and not saved |
| 38 |  | 56 | 0x38 | current location | 2 | 0 | SRAM | read-only | -1 | -1 | step | Feedback the number of steps of the current position, each step is a minimum resolution angle; absolute position control mode, the maximum corresponding to the maximum effective angle |
| 3A |  | 58 | 0x3A | current speed | 2 | 0 | SRAM | read-only | -1 | -1 | step/s | Feedback of the current motor speed, the number of steps in a unit time (per second) |
| 3C |  | 60 | 0x3C | current load | 2 | 0 | SRAM | read-only | -1 | -1 | 0.001 | Voltage duty cycle of current control output drive motor |
| 3E |  | 62 | 0x3E | current voltage | 1 | 0 | SRAM | read-only | -1 | -1 | 0.1V | The Current operating voltage of the servo |
| 3F |  | 63 | 0x3F | Current temperature | 1 | 0 | SRAM | read-only | -1 | -1 | °C | Internal working circuit of the current servo |
| 40 |  | 64 | 0x40 | Asynchronous write sign | 1 | 0 | SRAM | read-only | -1 | -1 | no | When writing instructions asynchronously, the flag bit |
| 41 |  | 65 | 0x41 | servo state | 1 | 0 | SRAM | read-only | -1 | -1 | no | Bit0 Bit1 Bit2 Bit3 Bit4 Bit5 The corresponding bit is set to 1 to indicate that the corresponding error occurs.
Voltage no temperature no overload corresponding bit 0 is no corresponding error. |
| 42 |  | 66 | 0x42 | mobile logo | 1 | 0 | SRAM | read-only | -1 | -1 | no | The servo is marked 1 when moving and 0 when stops. |