import time
import board
import busio
import digitalio
import time

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

led.value = True

uart = busio.UART(board.GP4, board.GP5, baudrate=115200)

ctr = 0
start = time.monotonic()
output = 1000

import time
import board
import digitalio

import struct

row_pin_map = {
    3: board.GP14,
    4: board.GP15,
    2: board.GP11,
    1: board.GP8,
}
col_pin_map = {
    6: board.GP16,
    5: board.GP17,
    3: board.GP18,
    2: board.GP19,
    1: board.GP22,
    4: board.GP26,
}

row_pins = []
col_pins = []

for idx, pin in col_pin_map.items():
    key_pin = digitalio.DigitalInOut(pin)
    key_pin.direction = digitalio.Direction.INPUT
    key_pin.pull = digitalio.Pull.UP
    col_pins.append(key_pin)

for idx, pin in row_pin_map.items():
    key_pin = digitalio.DigitalInOut(pin)
    key_pin.direction = digitalio.Direction.OUTPUT
    key_pin.value = True
    row_pins.append(key_pin)

counter = 0
prev_time = time.monotonic()


arr = ["0"]*(len(row_pins)*len(col_pins))

print(len(arr))

while True:
    i = 0
    for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
        row.value = False
        for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
            
            out = not col.value
            if out:
                arr[i] = b"1"
                print(row_name, col_name)
            else:
                arr[i] = b"0"

                pass
            i += 1

        row.value = True
    to_write = b"".join(arr)
    #print(to_write)
    uart.write(to_write)

    ctr += 1
    if ctr % 1000 == 0:
        print(time.monotonic() - start)
        start = time.monotonic()