import time
import board
import digitalio
from state_machine import StateMachine, StartState, WaitState, KeyPressState, KeyTapState

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode


class Key:
    def __init__(self, kb):
        self.kb = kb
        self.kc = Keycode.CONTROL  # keycode?
        # self.is_down = False
        # example of modtap
        # ss = StartState("Start", None)
        # kp = KeyTapState("Press A", self.kb, self.kc, ss)
        # kpb = KeyPressState("Press B", self.kb, Keycode.B, ss)
        # wst = WaitState("Wait", 0.1, kpb, kp)
        # ws = WaitState("Wait", 5 / 1000, wst, ss)
        # ss.next_state = ws

        ss = StartState("Start", None)
        wait1 = WaitState("Wait1", 0.1, None, None)
        kp = KeyTapState("Press A", self.kb, self.kc, ss)
        kpp = KeyPressState("Press A", self.kb, self.kc, ss)
        kp2 = KeyTapState("Press B", self.kb, Keycode.B, ss)
        kp2p = KeyPressState("Press B", self.kb, [Keycode.CONTROL, Keycode.ALT], ss)
        wait2 = WaitState("Wait2", 0.1, kp, None, inverted=True)
        wait3 = WaitState("Wait3", 0.1, None, None)
        wait4 = WaitState("Wait4", 0.1, kp2, None, inverted=True)
        wait1.fail_state = wait2
        wait1.success_state = kpp
        wait2.fail_state = wait3
        wait3.fail_state = wait4
        wait3.success_state = kp2p
        ss.next_state = wait1

        self.sm = StateMachine([ss, wait1, kp, wait2, wait3, wait4, kp2])

    # def on_down(self):
    #     print(time.monotonic_ns(), "key down")

    # def on_up(self):
    #     print(time.monotonic_ns(), "key up")

    def update(self, val):
        self.sm.update(val)
        # if val is True:
        #     self.downed()
        # if val is False:
        #     self.upped()

    # def downed(self):
    #     # print("downed called")
    #     if self.is_down:
    #         return
    #     self.is_down = True
    #     self.on_down()

    # def upped(self):
    #     # print("upped called")
    #     if not self.is_down:
    #         return
    #     if self.is_down:
    #         self.is_down = False
    #         self.on_up()


# The pins we'll use, each will have an internal pullup
row_pin_names = [board.GP2, board.GP3]
col_pin_names = [board.GP0, board.GP1]
# columns are inputs?

row_pins = []
col_pins = []

for pin in col_pin_names:
    key_pin = digitalio.DigitalInOut(pin)
    key_pin.direction = digitalio.Direction.INPUT
    key_pin.pull = digitalio.Pull.UP
    col_pins.append(key_pin)

for pin in row_pin_names:
    key_pin = digitalio.DigitalInOut(pin)
    key_pin.direction = digitalio.Direction.OUTPUT
    key_pin.value = True
    row_pins.append(key_pin)

prev_time = time.monotonic_ns()


time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

k = Key(keyboard)

print("loop starting")

while True:
    # Check each pin
    for row, row_name in zip(row_pins, row_pin_names):
        row.value = False
        for col, col_name in zip(col_pins, col_pin_names):
            # tim = time.monotonic_ns() - prev_time
            # print(col.value)
            # k.update(not col.value)
            if not col.value:
                print(row_name, col_name)
            prev_time = time.monotonic_ns()
        row.value = True

    time.sleep(0.0)
