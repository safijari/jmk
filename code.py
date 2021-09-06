import time
import board
import digitalio
from state_machine import (
    StateMachine,
    StartState,
    WaitState,
    KeyPressState,
    KeyTapState,
)

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode


class PlainJaneKey:
    def __init__(self, kb, kc):
        self.kb = kb
        self.kc = kc  # keycode?

        ss = StartState("Start", None)
        kpb = KeyPressState("Press " + str(kc), self.kb, self.kc, ss)
        ss.next_state = kpb

        self.sm = StateMachine([ss, kpb])

    def update(self, val):
        self.sm.update(val)


class TapDance:
    def __init__(self, kb, kc1, kc2):
        self.kb = kb
        # self.is_down = False
        # example of modtap
        # ss = StartState("Start", None)
        # kp = KeyTapState("Press A", self.kb, self.kc, ss)
        # kpb = KeyPressState("Press B", self.kb, Keycode.B, ss)
        # wst = WaitState("Wait", 0.1, kpb, kp)
        # ws = WaitState("Wait", 5 / 1000, wst, ss)
        # ss.next_state = ws

        ss = StartState("Start", None)
        wait1 = WaitState("Wait1", 0.05, None, None)
        kp = KeyTapState("Press A", self.kb, kc1, ss)
        kpp = KeyPressState("Press A", self.kb, kc1, ss)
        kp2 = KeyTapState("Press B", self.kb, kc2, ss)
        kp2p = KeyPressState("Press B", self.kb, [Keycode.CONTROL, Keycode.ALT], ss)
        wait2 = WaitState("Wait2", 0.05, kp, None, inverted=True)
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
row_pin_map = {
    1: board.GP14,
    2: board.GP15,
    3: board.GP12,
    4: board.GP10,
}
col_pin_map = {
    1: board.GP4,
    2: board.GP3,
    3: board.GP5,
    4: board.GP6,
    5: board.GP7,
    6: board.GP9,
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

prev_time = time.monotonic_ns()


time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

k = Key(keyboard)

kc = Keycode


def mk(kc):
    return PlainJaneKey(keyboard, kc)


layout_right = {
    1: {
        1: mk(kc.BACKSLASH),
        2: mk(kc.P),
        3: mk(kc.O),
        4: mk(kc.I),
        5: mk(kc.U),
        6: mk(kc.Y),
    },
    2: {1: mk(kc.QUOTE), 2: mk(kc.SEMICOLON), 3: mk(kc.L), 4: mk(kc.K), 5: mk(kc.J), 6: mk(kc.H)},
    3: {1: mk(kc.RIGHT_SHIFT), 2: mk(kc.FORWARD_SLASH), 3: mk(kc.L), 4: mk(kc.K), 5: mk(kc.J), 6: mk(kc.H)},
    # 4: {1: "KEY_RIGHT_SHIFT", 2: "/", 3: ".", 4: ",", 5: "m", 6: "n",},
    # 5: {1: "LAYER", 2: "]", 3: "[", 4: "NO_OP", 5: "NO_OP",},
    # 6: {5: " ", 6: "KEY_RIGHT_CTRL",},
    # 7: {5: "LAYER", 6: "KEY_RIGHT_GUI",},
    # 8: {5: "KEY_RETURN", 6: "KEY_RIGHT_ALT",},
}

print("loop starting")

counter = 0
prev_time = time.monotonic()

while True:
    # Check each pin
    for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
        row.value = False
        col_layout = layout_right.get(row_idx, {})
        for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
            # tim = time.monotonic_ns() - prev_time
            # print(col.value)
            # k.update(not col.value)

            out = not col.value
            sm = col_layout.get(col_idx, None)
            if out:
                print(row_name, col_name)
            if sm:
                sm.update(out)
        row.value = True

    counter += 1

    # if counter % 100 == 0:
    #     print(((time.monotonic() - prev_time)/100*1000))
    #     prev_time = time.monotonic()
