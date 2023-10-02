import time
import board
import busio
import digitalio
import time

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

led.value = True

uart = busio.UART(board.GP01, board.GP13, baudrate=115200)

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
    2: board.GP6,
    1: board.GP8,
}
col_pin_map = {
    6: board.GP16,
    5: board.GP17,
    3: board.GP28,
    2: board.GP21,
    1: board.GP20,
    4: board.GP27,
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


arr = [b"0"]*(len(row_pins)*len(col_pins))
arr.append(b"\n")

print(len(arr))

while True:
    i = 0
    for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
        row.value = False
        for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
            
            out = not col.value
            if out:
                arr[i] = b"1"
            else:
                arr[i] = b"0"

                pass
            i += 1

        row.value = True
    to_write = b"".join(arr)
    print(to_write)
    oot = uart.write(to_write)

    ctr += 1
    if ctr % 100 == 0:
        print(time.monotonic() - start)
        start = time.monotonic()
        
    #time.sleep(23/1000)