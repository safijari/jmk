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
    KeySequenceState,
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
import sys


uart = busio.UART(board.GP16, board.GP17, baudrate=115200, receiver_buffer_size=256)

MOUSE_MOVE_SPEED = 7
MOUSE_MOVE_ACCEL = 1.2
MOUSE_SCROLL_SPEED = 3

enumerated = False
while not enumerated:
    try:
        mouse = Mouse(usb_hid.devices)
        keyboard = Keyboard(usb_hid.devices)
        concon = ConsumerControl(usb_hid.devices)
        enumerated = True
    except Exception:
        pass


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
        return "keyseq"


class Sequence:
    def __init__(self, kc_list, delay=0.1):
        self.kb = keyboard
        self.kc = kc_list

        self.sm = StateMachine(
            {
                "start": StartState("Start", "key_seq"),
                "key_seq": KeySequenceState(
                    "Seq " + str(kc), self.kb, self.kc, "start", delay=delay
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
    def __init__(self, kc1, kc2, T=0.2, taptap=False, permissive_hold=True):
        kb = keyboard
        act2 = (
            KeyPressState("Act2Press", kb, kc2, "start")
            if not taptap
            else KeyTapState("Act2Tap", kb, kc2, "start")
        )
        self.sm = StateMachine(
            {
                "start": StartState("Start", "act1wait"),
                "act1wait": WaitState(
                    "Act1Wait1",
                    T,
                    "act2press",
                    "act1tap",
                    success_on_permissive_hold=permissive_hold,
                ),
                "act1tap": KeyTapState("Act1Tap", kb, kc1, "start"),
                "act2press": act2,
            }
        )

    def update(self, val):
        self.sm.update(val)

    @property
    def type(self):
        return "modtap"


class TapDance:
    def __init__(self, kc1, kc2, kc1hold=None, kc2hold=None, T=0.2):
        kb = keyboard
        self.kb = kb
        self.kc1 = kc1
        self.kc2 = kc2
        if kc1hold is None:
            self.kc1hold = kc1
        if kc2hold is None:
            self.kc2hold = kc2

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
                "act1press": KeyPressState("Act1Press", self.kb, self.kc1hold, "start"),
                "act1tap": KeyTapState("Act1Tap", self.kb, self.kc1, "start"),
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
                "act2press": KeyPressState("Act2Press", self.kb, self.kc2hold, "start"),
                "act2tap": KeyTapState("Act2Tap", self.kb, self.kc2, "start"),
            }
        )

    @property
    def type(self):
        return "tapdance"

    def update(self, val):
        self.sm.update(val)


# The pins we'll use, each will have an internal pullup
row_pin_map = {
    1: board.GP22,
    2: board.GP13,
    3: board.GP14,
    4: board.GP15,
}
col_pin_map = {
    1: board.GP12,
    2: board.GP11,
    3: board.GP10,
    4: board.GP9,
    5: board.GP7,
    6: board.GP6,
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

layers_dict = {
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
                6: TapDance(kc.RIGHT_CONTROL, [kc.RIGHT_ALT]),
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
                # 5: ModTap(kc.V, [kc.LEFT_CONTROL, kc.V], T=0.3, taptap=True, permissive_hold=False),
                5: Key(kc.V),
                6: Key(kc.B),
            },
            4: {
                4: Key(kc.LEFT_GUI),
                5: "nav",
                6: ModTap(kc.ESCAPE, kc.LEFT_CONTROL),
            },
        },
    },
    "numbers": {
        "right": {
            1: {
                1: ModTap(
                    kc.BACKSLASH, [kc.LEFT_CONTROL, kc.LEFT_SHIFT, kc.BACKSLASH], T=0.3
                ),
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
                2: Key(kc.RIGHT_BRACKET),
                3: Key(kc.LEFT_BRACKET),
                4: Key([kc.RIGHT_SHIFT, kc.RIGHT_BRACKET]),
                5: Key([kc.RIGHT_SHIFT, kc.LEFT_BRACKET]),
                6: Key(kc.SPACE),
            },
        },
        "left": {
            1: {
                1: Key(kc.GRAVE_ACCENT),
                2: Key([kc.LEFT_SHIFT, kc.ONE]),
                3: Key([kc.LEFT_SHIFT, kc.TWO]),
                4: Key([kc.LEFT_SHIFT, kc.THREE]),
                5: Key([kc.LEFT_SHIFT, kc.FOUR]),
                6: Key([kc.LEFT_SHIFT, kc.FIVE]),
            },
            2: {
                2: Key(kc.ONE),
                3: Key(kc.TWO),
                4: Key(kc.THREE),
                5: Key(kc.FOUR),
                6: Key(kc.FIVE),
            },
        },
    },
    "nav": {
        "right": {
            1: {
                1: Key([kc.QUOTE, kc.RIGHT_SHIFT]),
                2: MouseKey(Mouse.LEFT_BUTTON),
                3: Key(kc.END),
                4: MouseMove(0, 0, MOUSE_SCROLL_SPEED),
                5: MouseMove(0, 0, -MOUSE_SCROLL_SPEED),
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
                # 1: Sequence([kc.RETURN, kc.LEFT_ARROW, kc.MINUS, kc.RETURN], delay=0.01),
                2: MouseKey(Mouse.MIDDLE_BUTTON),
                3: Key([kc.RIGHT_ARROW, kc.RIGHT_CONTROL]),
                4: Key([kc.RIGHT_ARROW, kc.RIGHT_ALT]),
                5: Key([kc.LEFT_ARROW, kc.RIGHT_ALT]),
                6: Key([kc.LEFT_ARROW, kc.RIGHT_CONTROL]),
            },
            4: {4: Key([kc.LEFT_GUI]),},
        },
        "left": {
            1: {
                1: Key([kc.LEFT_SHIFT, kc.GRAVE_ACCENT]),
                4: MouseMove(
                    0, -MOUSE_MOVE_SPEED, 0, MOUSE_MOVE_ACCEL, MOUSE_MOVE_ACCEL
                ),
                6: Key([kc.LEFT_ALT, kc.UP_ARROW]),
            },
            2: {
                2: Key(kc.LEFT_ALT),
                3: MouseMove(
                    -MOUSE_MOVE_SPEED, 0, 0, MOUSE_MOVE_ACCEL, MOUSE_MOVE_ACCEL
                ),
                4: MouseMove(
                    0, MOUSE_MOVE_SPEED, 0, MOUSE_MOVE_ACCEL, MOUSE_MOVE_ACCEL
                ),
                5: MouseMove(
                    MOUSE_MOVE_SPEED, 0, 0, MOUSE_MOVE_ACCEL, MOUSE_MOVE_ACCEL
                ),
                6: Key([kc.LEFT_ALT, kc.DOWN_ARROW]),
            },
            3: {
                2: ConsumerKey(cc.SCAN_NEXT_TRACK),
                3: ConsumerKey(cc.PLAY_PAUSE),
                5: ConsumerKey(cc.VOLUME_INCREMENT),
                4: ConsumerKey(cc.VOLUME_DECREMENT),
                6: ConsumerKey(cc.MUTE),
            },
        },
    },
}

layer_info = {"left": {}, "right": {}}

permissive_hold_lists = {"left": [], "right": []}

state = {"right": [], "left": []}
prev_state = {"right": [], "left": []}
final = {"right": [], "left": []}
layers = {name: {"right": [], "left": []} for name in layers_dict}

for side in ["right", "left"]:
    for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
        for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
            state[side].append(False)
            prev_state[side].append(False)
            final[side].append(None)
            for layer in layers:
                layers[layer][side].append(
                    layers_dict[layer][side].get(row_idx, {}).get(col_idx, None)
                )

for side in ["left", "right"]:
    for idx, val in enumerate(layers["base"][side]):
        final[side][idx] = val
        if val in layers:
            layer_info[side][val] = idx
            continue
        if val is not None and val.type in ["modtap", "tapdance"]:
            permissive_hold_lists[side].append(idx)

print(layer_info)
print(permissive_hold_lists)

print("loop starting")

counter = 0
prev_time = time.monotonic()

fails = 0
while True:
    try:
        # state_read_start = time.monotonic_ns()
        uart.reset_input_buffer()
        left_half_stuff = uart.readline()
        while len(left_half_stuff) != 25:
            fails += 1
            left_half_stuff = uart.readline()
        # print(fails)
        flips = {"left": set(), "right": set()}
        # gc.collect()
        idx = 0
        for row, (row_idx, row_name) in zip(row_pins, row_pin_map.items()):
            row.value = False
            for col, (col_idx, col_name) in zip(col_pins, col_pin_map.items()):
                prev_state_val_right = state["right"][idx]
                prev_state["right"][idx] = prev_state_val_right
                cur_state_val_right = not col.value
                state["right"][idx] = cur_state_val_right
                if cur_state_val_right and not prev_state_val_right:
                    flips["right"].add(idx)

                prev_state_val = state["left"][idx]
                prev_state["left"][idx] = prev_state_val
                cur_state_val = chr(left_half_stuff[idx]) == "1"
                state["left"][idx] = cur_state_val
                if cur_state_val and not prev_state_val:
                    flips["left"].add(idx)

                idx += 1
            row.value = True

        # state_read_end = time.monotonic_ns()
        # print("took for matrix read", (state_read_end - state_read_start)/1000000.0)
        counter += 1

        # start_flips = time.monotonic_ns()

        layer = "base"

        for side in ["left", "right"]:
            for possible_layer, idx in layer_info[side].items():
                if state[side][idx]:
                    layer = possible_layer

        base_layer = layers["base"]
        le_layer = layers[layer]

        for side in ["left", "right"]:
            for idx in permissive_hold_lists[side]:
                cond = False
                for side2 in ["left", "right"]:
                    if side2 == side:
                        cond = len(flips[side2].difference(set([idx])))
                    else:
                        cond = len(flips[side2])
                    if cond:
                        break
                if cond:
                    base_layer[side][idx].sm.update(state[side][idx], True)

        # end_flips = time.monotonic_ns()

        # print("took for flips read", (end_flips - start_flips)/1000000.0)

        for side in ["left", "right"]:
            le_state = state[side]
            le_final = final[side]
            le_layer_side = le_layer[side]
            base_layer_side = base_layer[side]
            layer_info_side = layer_info[side]
            for idx, base_key in enumerate(base_layer_side):
                key_state = le_state[idx]
                key_final = le_final[idx]

                if key_final in layer_info_side or key_final is None:
                    continue

                if key_final.sm.cur_state_type == "start":
                    if le_layer_side[idx] is not None:
                        le_final[idx] = le_layer_side[idx]
                    else:
                        le_final[idx] = key_final
                actual_final = le_final[idx]
                if actual_final in layer_info[side]:
                    continue

                actual_final.sm.update(key_state)

        iters = 500
        if counter % iters == 0:
            print(((time.monotonic() - prev_time) / iters * 1000), (fails / iters))
            prev_time = time.monotonic()
            fails = 0
    except Exception as e:
        sys.print_exception(e)
