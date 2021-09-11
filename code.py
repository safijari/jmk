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

import busio
import gc

uart = busio.UART(board.GP16, board.GP17, baudrate=115200)


class Key:
    def __init__(self, kb, kc):
        self.kb = kb
        self.kc = kc  # keycode?

        self.sm = StateMachine(
            {
                "start": StartState("Start", "key_press"),
                "key_press": KeyPressState(
                    "Press " + str(kc), self.kb, self.kc, "start"
                ),
            }
        )

    def __repr__(self):
        return f"{self.kc}"

    def update(self, val):
        self.sm.update(val)

    @property
    def type(self):
        return "key"


class ModTap:
    def __init__(self, kb, kc1, kc2):
        T = 0.15
        self.sm = StateMachine(
            {
                "start": StartState("Start", "act1wait"),
                "act1wait": WaitState(
                    "Act1Wait1",
                    T,
                    "act2press",
                    "act1tap",
                    success_on_permissive_hold=True,
                ),
                "act1tap": KeyTapState("Act1Tap", kb, kc1, "start"),
                "act2press": KeyPressState("Act2Press", kb, kc2, "start"),
            }
        )

    def update(self, val):
        self.sm.update(val)

    @property
    def type(self):
        return "modtap"


class TapDance:
    def __init__(self, kb, kc1, kc2):
        self.kb = kb

        T = 0.15

        self.sm = StateMachine(
            {
                "start": StartState("Start", "act1wait"),
                "act1wait": WaitState(
                    "Act1Wait1",
                    T,
                    "act1press",
                    "act1tapwait",
                    success_on_permissive_hold=True,
                ),
                "act1tapwait": WaitState(
                    "Act1Wait2", T, "act1tap", "act2wait", inverted=True
                ),
                "act1press": KeyPressState("Act1Press", kb, kc1, "start"),
                "act1tap": KeyTapState("Act1Tap", kb, kc1, "start"),
                "act2wait": WaitState(
                    "Act2Wait1",
                    T,
                    "act2press",
                    "act2tapwait",
                    success_on_permissive_hold=True,
                ),
                "act2tapwait": WaitState(
                    "Act2Wait2", T, "act2tap", "start", inverted=True
                ),
                "act2press": KeyPressState("Act2Press", kb, kc2, "start"),
                "act2tap": KeyTapState("Act2Tap", kb, kc2, "start"),
            }
        )

    @property
    def type(self):
        return "tapdance"

    def update(self, val):
        self.sm.update(val)


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



keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems

kc = Keycode
kb = keyboard


def mk(kc):
    return Key(keyboard, kc)


layers = {
    "base": {
        "right": {
            1: {
                1: mk(kc.BACKSPACE),
                2: mk(kc.P),
                3: mk(kc.O),
                4: mk(kc.I),
                5: mk(kc.U),
                6: mk(kc.Y),
            },
            2: {
                1: mk(kc.RETURN),
                2: mk(kc.SEMICOLON),
                3: mk(kc.L),
                4: mk(kc.K),
                5: mk(kc.J),
                6: mk(kc.H),
            },
            3: {
                1: TapDance(keyboard, kc.RIGHT_SHIFT, kc.CAPS_LOCK),
                # 1: mk(kc.RIGHT_SHIFT),
                2: mk(kc.FORWARD_SLASH),
                3: mk(kc.PERIOD),
                4: mk(kc.COMMA),
                5: mk(kc.M),
                6: mk(kc.N),
            },
            4: {4: mk(kc.SPACE), 5: "numbers", 6: mk(kc.RIGHT_CONTROL)},
        },
        "left": {
            1: {
                1: mk(kc.EQUALS),
                2: mk(kc.Q),
                3: mk(kc.W),
                4: mk(kc.E),
                5: mk(kc.R),
                6: mk(kc.T),
            },
            2: {
                1: ModTap(kb, kc.TAB, kc.LEFT_GUI),
                2: mk(kc.A),
                3: mk(kc.S),
                4: mk(kc.D),
                5: mk(kc.F),
                6: mk(kc.G),
            },
            3: {
                1: TapDance(keyboard, kc.LEFT_SHIFT, kc.CAPS_LOCK),
                # 1: mk(kc.LEFT_SHIFT),
                2: mk(kc.Z),
                3: mk(kc.X),
                4: mk(kc.C),
                5: mk(kc.V),
                6: mk(kc.B),
            },
            4: {
                4: TapDance(keyboard, kc.LEFT_GUI, [kc.LEFT_GUI, kc.LEFT_SHIFT]),
                5: "nav",
                6: ModTap(kb, kc.ESCAPE, kc.LEFT_CONTROL),
            },
        },
    },
    "numbers": {
        "right": {
            1: {
                1: mk([kc.MINUS, kc.LEFT_SHIFT]),
                2: mk([kc.ZERO, kc.LEFT_SHIFT]),
                3: mk([kc.NINE, kc.LEFT_SHIFT]),
                4: mk([kc.EIGHT, kc.LEFT_SHIFT]),
                5: mk([kc.SEVEN, kc.LEFT_SHIFT]),
                6: mk([kc.SIX, kc.LEFT_SHIFT]),
            },
            2: {
                1: mk(kc.MINUS),
                2: mk(kc.ZERO),
                3: mk(kc.NINE),
                4: mk(kc.EIGHT),
                5: mk(kc.SEVEN),
                6: mk(kc.SIX),
            },
            3: {
                # 1: mk(kc.MINUS),
                2: mk(kc.RIGHT_BRACKET),
                3: mk(kc.LEFT_BRACKET),
                # 4: mk(kc.EIGHT),
                # 5: mk(kc.SEVEN),
                # 6: mk(kc.SIX),
            },
        },
        "left": {
            2: {
                # 1: mk(kc.MINUS),
                2: mk(kc.ONE),
                3: mk(kc.TWO),
                4: mk(kc.THREE),
                5: mk(kc.FOUR),
                6: mk(kc.FIVE),
            },
            1: {
                # 1: mk(kc.MINUS),
                2: mk([kc.LEFT_SHIFT, kc.ONE]),
                3: mk([kc.LEFT_SHIFT, kc.TWO]),
                4: mk([kc.LEFT_SHIFT, kc.THREE]),
                5: mk([kc.LEFT_SHIFT, kc.FOUR]),
                6: mk([kc.LEFT_SHIFT, kc.FIVE]),
            },
        },
    },
    "nav": {
        "right": {
            2: {
                # 1: mk(kc.QUOTE),
                # 2: mk(kc.ZERO),
                3: mk(kc.RIGHT_ARROW),
                4: mk(kc.UP_ARROW),
                5: mk(kc.DOWN_ARROW),
                6: mk(kc.LEFT_ARROW),
            },
        },
        "left": {},
    },
}

layer_info = {"left": {}, "right": {}}

permissive_hold_lists = {"left": [], "right": []}

for side in ["left", "right"]:
    for row_idx, row_info in layers["base"][side].items():
        for col_idx, col_info in row_info.items():
            if col_info in layers:
                layer_info[side][col_info] = (row_idx, col_idx)
                continue
            if col_info.type in ["modtap", "tapdance"]:
                permissive_hold_lists[side].append((row_idx, col_idx))

print(layer_info)
print(permissive_hold_lists)

final = {
    "right": {
        1: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None,},
        2: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None,},
        3: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None,},
        4: {4: None, 5: None, 6: None},
    },
    "left": {
        1: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None,},
        2: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None,},
        3: {1: None, 2: None, 3: None, 4: None, 5: None, 6: None,},
        4: {4: None, 5: None, 6: None},
    },
}

prev_state = {
    "right": {
        1: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        2: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        3: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        4: {4: False, 5: False, 6: False},
    },
    "left": {
        1: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        2: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        3: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        4: {4: False, 5: False, 6: False},
    },
}

state = {
    "right": {
        1: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        2: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        3: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        4: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
    },
    "left": {
        1: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        2: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        3: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
        4: {1: False, 2: False, 3: False, 4: False, 5: False, 6: False,},
    },
}

print("loop starting")

counter = 0
prev_time = time.monotonic()

while True:
    gc.collect()
    flips = {"left": set(), "right": set()}
    # Check each pin
    left_half_stuff = uart.readline()
    if not left_half_stuff or len(left_half_stuff) != 25:
        print("could not read left half, will retry")
        continue
    for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
        row.value = False
        for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
            prev_state_val = state["right"][row_idx][col_idx]
            prev_state["right"][row_idx][col_idx] = prev_state_val
            cur_state_val = not col.value
            state["right"][row_idx][col_idx] = cur_state_val
            if cur_state_val and not prev_state_val:
                flips["right"].add((row_idx, col_idx))
        row.value = True

    j = 0
    for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
        for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
            prev_state_val = state["left"][row_idx][col_idx]
            prev_state["left"][row_idx][col_idx] = prev_state_val
            cur_state_val = chr(left_half_stuff[j]) == "1"
            state["left"][row_idx][col_idx] = cur_state_val
            if cur_state_val and not prev_state_val:
                flips["left"].add((row_idx, col_idx))
            j += 1

    counter += 1

    layer = "base"

    for side in ["left", "right"]:
        for possible_layer, (row_idx, col_idx) in layer_info[side].items():
            if state[side].get(row_idx, {}).get(col_idx, False):
                layer = possible_layer

    base_layer = layers["base"]
    le_layer = layers[layer]

    for side in ["left", "right"]:
        for (row, col) in permissive_hold_lists[side]:
            cond = False
            for side2 in ["left", "right"]:
                if side2 == side:
                    cond = len(flips[side2].difference(set([(row, col)])))
                else:
                    cond = len(flips[side2])
                if cond:
                    break
            if cond:
                # print("would have permissived", side)
                print(row, col)
                base_layer[side][row][col].sm.update(state[side][row][col], True)

    for side in ["left", "right"]:
        le_state = state[side]
        le_final = final[side]
        le_layer_side = le_layer[side]
        base_layer_side = base_layer[side]
        for row_idx, row_name in row_pin_map.items():
            if row_idx not in le_state:
                continue
            col_state = le_state[row_idx]
            col_final = le_final[row_idx]
            col_layer = le_layer_side.get(row_idx, {})
            col_base = base_layer_side[row_idx]
            for col_idx, col_name in col_pin_map.items():
                if col_idx not in col_final:
                    continue
                key_state = col_state[col_idx]
                key_final = col_final[col_idx]
                if key_final in layer_info[side]:
                    continue
                if key_final is None or key_final.sm.cur_state_type == "start":
                    col_final[col_idx] = col_layer.get(
                        col_idx, col_base.get(col_idx, None)
                    )
                actual_final = col_final[col_idx]
                if actual_final in layer_info[side]:
                    continue

                actual_final.sm.update(key_state)

    iters = 50
    if counter % iters == 0:
        print(((time.monotonic() - prev_time) / iters * 1000))
        prev_time = time.monotonic()
