import time
import board
import digitalio
from state_machine import (
    StateMachine,
    StartState,
    WaitState,
    KeyPressState,
    KeyTapState,
    MouseMoveState,
)

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

import busio
import gc
from adafruit_hid.mouse import Mouse

mouse = Mouse(usb_hid.devices)

uart = busio.UART(board.GP16, board.GP17, baudrate=115200, receiver_buffer_size=256)

keyboard = Keyboard(usb_hid.devices)
concon = ConsumerControl(usb_hid.devices)
# keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

# time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems


class Key:
    def __init__(self, kc):
        self.kb = keyboard
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


class ConsumerKey:
    def __init__(self, kc):
        self.kb = concon
        self.kc = kc  # keycode?

        self.sm = StateMachine(
            {
                "start": StartState("Start", "key_press"),
                "key_press": KeyPressState(
                    "Press " + str(kc),
                    self.kb,
                    self.kc,
                    "start",
                    release_without_kc=True,
                ),
            }
        )

    def __repr__(self):
        return f"{self.kc}"

    def update(self, val):
        self.sm.update(val)

    @property
    def type(self):
        return "cckey"


class MouseKey:
    def __init__(self, kc):
        self.kb = mouse
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
        return "mousekey"


class MouseMove:
    def __init__(self, dx, dy, dw=0, ax=1, ay=1):
        self.sm = StateMachine(
            {
                "start": StartState("Start", "key_press"),
                "key_press": MouseMoveState(
                    "MouseMove", mouse, dx, dy, "start", dw, ax, ay
                ),
            }
        )

    def __repr__(self):
        return f"{self.kc}"

    def update(self, val):
        self.sm.update(val)

    @property
    def type(self):
        return "mosuemove"


class ModTap:
    def __init__(self, kc1, kc2):
        kb = keyboard
        T = 0.2
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
    def __init__(self, kc1, kc2, kc1hold=None, kc2hold=None):
        kb = keyboard
        self.kb = kb
        if kc1hold is None:
            kc1hold = kc1
        if kc2hold is None:
            kc2hold = kc2

        T = 0.1

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
                    "Act1Wait2",
                    T,
                    "act1tap",
                    "act2wait",
                    inverted=True,
                    success_on_permissive_hold=True,
                ),
                "act1press": KeyPressState("Act1Press", kb, kc1hold, "start"),
                "act1tap": KeyTapState("Act1Tap", kb, kc1, "start"),
                "act2wait": WaitState(
                    "Act2Wait1",
                    T,
                    "act2press",
                    "act2tap",
                    success_on_permissive_hold=True,
                ),
                # "act2tapwait": WaitState(
                #     "Act2Wait2",
                #     T,
                #     "act2tap",
                #     "start",
                #     inverted=True,
                #     success_on_permissive_hold=True,
                # ),
                "act2press": KeyPressState("Act2Press", kb, kc2hold, "start"),
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


kc = Keycode
cc = ConsumerControlCode

layers = {
    "base": {
        "right": {
            1: {
                1: Key(kc.MINUS),
                2: Key(kc.P),
                3: Key(kc.O),
                4: Key(kc.I),
                5: Key(kc.U),
                6: Key(kc.Y),
            },
            2: {
                1: Key(kc.LEFT_SHIFT),
                2: Key(kc.SEMICOLON),
                3: Key(kc.L),
                4: Key(kc.K),
                5: Key(kc.J),
                6: Key(kc.H),
            },
            3: {
                1: Key(kc.RETURN),
                2: Key(kc.FORWARD_SLASH),
                3: Key(kc.PERIOD),
                4: Key(kc.COMMA),
                5: Key(kc.M),
                6: Key(kc.N),
            },
            4: {
                4: Key(kc.SPACE),
                5: "numbers",
                6: TapDance(kc.RIGHT_CONTROL, [kc.RIGHT_CONTROL, kc.RIGHT_ALT]),
            },
        },
        "left": {
            1: {
                1: Key(kc.EQUALS),
                2: Key(kc.Q),
                3: Key(kc.W),
                4: Key(kc.E),
                5: Key(kc.R),
                6: Key(kc.T),
            },
            2: {
                1: ModTap(kc.TAB, kc.LEFT_SHIFT),
                2: Key(kc.A),
                3: Key(kc.S),
                4: Key(kc.D),
                5: Key(kc.F),
                6: Key(kc.G),
            },
            3: {
                1: Key(kc.BACKSPACE),
                2: Key(kc.Z),
                3: Key(kc.X),
                4: Key(kc.C),
                5: Key(kc.V),
                6: Key(kc.B),
            },
            4: {
                4: TapDance(kc.LEFT_GUI, [kc.LEFT_GUI, kc.LEFT_SHIFT]),
                5: "nav",
                6: ModTap(kc.ESCAPE, kc.LEFT_CONTROL),
            },
        },
    },
    "numbers": {
        "right": {
            1: {
                1: Key(kc.BACKSLASH),
                2: Key([kc.ZERO, kc.LEFT_SHIFT]),
                3: Key([kc.NINE, kc.LEFT_SHIFT]),
                4: Key([kc.EIGHT, kc.LEFT_SHIFT]),
                5: Key([kc.SEVEN, kc.LEFT_SHIFT]),
                6: Key([kc.SIX, kc.LEFT_SHIFT]),
            },
            2: {
                1: Key(kc.PERIOD),
                2: Key(kc.ZERO),
                3: Key(kc.NINE),
                4: Key(kc.EIGHT),
                5: Key(kc.SEVEN),
                6: Key(kc.SIX),
            },
            3: {
                # 1: Key(kc.MINUS),
                2: Key(kc.RIGHT_BRACKET),
                3: Key(kc.LEFT_BRACKET),
                4: Key([kc.RIGHT_SHIFT, kc.RIGHT_BRACKET]),
                5: Key([kc.RIGHT_SHIFT, kc.LEFT_BRACKET]),
                6: Key(kc.SPACE),
                # 5: Key(kc.SEVEN),
                # 6: Key(kc.SIX),
            },
        },
        "left": {
            2: {
                # 1: Key(kc.MINUS),
                1: TapDance(kc.LEFT_SHIFT, kc.CAPS_LOCK),
                2: Key(kc.ONE),
                3: Key(kc.TWO),
                4: Key(kc.THREE),
                5: Key(kc.FOUR),
                6: Key(kc.FIVE),
            },
            1: {
                1: Key(kc.GRAVE_ACCENT),
                2: Key([kc.LEFT_SHIFT, kc.ONE]),
                3: Key([kc.LEFT_SHIFT, kc.TWO]),
                4: Key([kc.LEFT_SHIFT, kc.THREE]),
                5: Key([kc.LEFT_SHIFT, kc.FOUR]),
                6: Key([kc.LEFT_SHIFT, kc.FIVE]),
            },
        },
    },
    "nav": {
        "right": {
            1: {
                1: Key([kc.QUOTE, kc.RIGHT_SHIFT]),
                2: MouseKey(Mouse.LEFT_BUTTON),
                3: Key(kc.END),
                4: MouseMove(0, 0, 2),
                5: MouseMove(0, 0, -2),
                6: Key(kc.HOME),
            },
            2: {
                1: Key(kc.QUOTE),
                2: MouseKey(Mouse.RIGHT_BUTTON),
                3: Key(kc.RIGHT_ARROW),
                4: Key(kc.UP_ARROW),
                5: Key(kc.DOWN_ARROW),
                6: Key(kc.LEFT_ARROW),
            },
            3: {
                2: MouseKey(Mouse.MIDDLE_BUTTON),
                3: Key([kc.RIGHT_ARROW, kc.RIGHT_CONTROL]),
                4: Key([kc.RIGHT_ARROW, kc.RIGHT_ALT]),
                5: Key([kc.LEFT_ARROW, kc.RIGHT_ALT]),
                6: Key([kc.LEFT_ARROW, kc.RIGHT_CONTROL]),
            },
        },
        "left": {
            1: {
                4: MouseMove(0, -13, 0, 1.05, 1.05),
                6: Key([kc.LEFT_ALT, kc.UP_ARROW]),
            },
            2: {
                1: Key(kc.CAPS_LOCK),
                3: MouseMove(-13, 0, 0, 1.05, 1.05),
                4: MouseMove(0, 13, 0, 1.05, 1.05),
                5: MouseMove(13, 0, 0, 1.05, 1.05),
                6: Key([kc.LEFT_ALT, kc.DOWN_ARROW]),
            },
            3: {
                6: ConsumerKey(cc.VOLUME_INCREMENT),
                5: ConsumerKey(cc.VOLUME_DECREMENT),
                4: ConsumerKey(cc.MUTE),
            },
        },
    },
}

layer_info = {"left": {}, "right": {}}

permissive_hold_lists = {"left": [], "right": []}

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


for side in ["left", "right"]:
    for row_idx, row_info in layers["base"][side].items():
        for col_idx, col_info in row_info.items():
            final[side][row_idx][col_idx] = layers["base"][side][row_idx][col_idx]
            if col_info in layers:
                layer_info[side][col_info] = (row_idx, col_idx)
                continue
            if col_info.type in ["modtap", "tapdance"]:
                permissive_hold_lists[side].append((row_idx, col_idx))

print(layer_info)
print(permissive_hold_lists)

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

fails = 0
while True:
    uart.reset_input_buffer()
    left_half_stuff = uart.readline()
    while len(left_half_stuff) != 25:
        fails += 1
        left_half_stuff = uart.readline()
    # print(fails)
    flips = {"left": set(), "right": set()}
    gc.collect()
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
                # print(row, col)
                base_layer[side][row][col].sm.update(state[side][row][col], True)

    for side in ["left", "right"]:
        le_state = state[side]
        le_final = final[side]
        le_layer_side = le_layer[side]
        base_layer_side = base_layer[side]
        for row_idx in base_layer_side:
            col_state = le_state[row_idx]
            col_final = le_final[row_idx]
            col_layer = le_layer_side.get(row_idx, {})
            col_base = base_layer_side[row_idx]
            for col_idx in col_base:
                key_state = col_state[col_idx]
                key_final = col_final[col_idx]
                if key_final in layer_info[side]:
                    continue
                if key_final.sm.cur_state_type == "start":
                    col_final[col_idx] = col_layer.get(col_idx, col_base.get(col_idx))
                actual_final = col_final[col_idx]
                if actual_final in layer_info[side]:
                    continue

                actual_final.sm.update(key_state)

    iters = 100
    if counter % iters == 0:
        print(((time.monotonic() - prev_time) / iters * 1000), (fails / iters))
        prev_time = time.monotonic()
        fails = 0
