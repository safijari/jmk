import time


class StartState:
    def __init__(self, name, next_state):
        self.name = name
        self.next_state = next_state

    def reset(self):
        pass

    def type(self):
        return "start"

    def into(self, smap, permissive_hold=False):
        return self

    def update(self, key_state, smap, permissive_hold=False):
        if key_state == False:
            return self
        else:
            # print("transitioning to next state from " + self.name)
            return smap[self.next_state]


class KeyPressState:
    def __init__(self, name, kb, kc, next_state):
        self.name = name
        self.next_state = next_state
        self.kb = kb
        self.kc = kc
        self.is_list = False
        if isinstance(kc, list):
            self.is_list = True
        self.reset()
        # self.release()

    def release(self):
        if not self.is_list:
            self.kb.release(self.kc)
        else:
            self.kb.release(*self.kc)

    def type(self):
        return "keypress"

    def reset(self):
        self.is_pressed = False

    def into(self, smap, permissive_hold=False):
        self.reset()
        return self.update(True, smap)

    def update(self, inp, smap, permissive_hold=False):
        if inp and not self.is_pressed:
            self.is_pressed = True
            try:
                if not self.is_list:
                    self.kb.press(self.kc)
                else:
                    self.kb.press(*self.kc)
            except ValueError:
                print("more than 6?")
            return self
        elif inp and self.is_pressed:
            return self
        elif not inp and not self.is_pressed:
            return self
        else:
            self.is_pressed = False
            self.release()
            return smap[self.next_state]


class KeyTapState:
    def __init__(self, name, kb, kc, next_state):
        self.name = name
        self.next_state = next_state
        self.kb = kb
        self.kc = kc
        self.is_list = False
        if isinstance(kc, list):
            self.is_list = True
        # self.kb.release(kc)

    def reset(self):
        pass

    def type(self):
        return "keytap"

    def into(self, smap, permissive_hold=False):
        self.reset()
        return self.update(True, smap)

    def update(self, inp, smap, permissive_hold=False):
        if not self.is_list:
            self.kb.press(self.kc)
            self.kb.release(self.kc)
        else:
            self.kb.press(*self.kc)
            self.kb.release(*self.kc)
        return smap[self.next_state]


class WaitState:
    def __init__(
        self,
        name,
        T,
        success_state,
        fail_state,
        inverted=False,
        success_on_permissive_hold=False,
    ):
        self.name = name
        self.T = T
        self.success_state = success_state
        self.fail_state = fail_state
        self.inverted = inverted
        self.success_on_permissive_hold = success_on_permissive_hold
        self.reset()

    def reset(self):
        self.wait_started = None
        self.in_wait = None

    def type(self):
        return "wait"

    def into(self, smap, permissive_hold=False):
        self.reset()
        return self.update(True, smap, permissive_hold)

    def update(self, inp, smap, permissive_hold=False):
        if self.inverted:
            inp = not inp

        if inp and self.success_on_permissive_hold and permissive_hold:
            # print(f"permissive hold {self.name} transitioning to success")
            return smap[self.success_state]

        if inp and not self.in_wait:
            self.in_wait = True
            self.wait_started = time.monotonic()
            return self
        elif inp and self.in_wait:
            if time.monotonic() - self.wait_started > self.T:
                # print(f"{self.name} transitioning to success")
                return smap[self.success_state]
            return self
        elif not inp and self.in_wait:
            if time.monotonic() - self.wait_started > self.T:
                # print(f"{self.name} transitioning to success")
                return smap[self.success_state]
            else:
                # print(f"{self.name} transitioning to failure")
                return smap[self.fail_state]
        else:
            # print("wait else?")
            return self


class StateMachine:
    def __init__(self, states):
        self.states = states
        self.reset()
        self.cur_state = states["start"]

    def reset(self):
        for s in self.states.values():
            s.reset()

    @property
    def cur_state_type(self):
        return self.cur_state.type()

    def update(self, inp, permissive_hold=False):
        next_state = self.cur_state.update(inp, self.states, permissive_hold)

        while next_state != self.cur_state:
            # print(next_state)
            # print(f"State changed to {str(next_state)}")
            if next_state:
                self.cur_state = next_state
                next_state = next_state.into(self.states, permissive_hold)
            else:
                break
        self.cur_state = next_state
        if self.cur_state is None:
            # print("machine died, rebooting")
            self.reset()
            self.cur_state = self.states[0]
