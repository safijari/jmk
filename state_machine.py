import time


class StartState:
    def __init__(self, name, next_state):
        self.name = name
        self.next_state = next_state

    def reset(self):
        pass

    def update(self, key_state):
        if key_state == False:
            return self
        else:
            print("transitioning to next state from " + self.name)
            return self.next_state


class KeyPressState:
    def __init__(self, name, kb, kc, next_state):
        self.name = name
        self.next_state = next_state
        self.kb = kb
        self.kc = kc
        self.is_list = isinstance(self.kc, list)
        self.reset()
        self.release()

    def release(self):
        if not self.is_list:
            self.kb.release(self.kc)
        else:
            self.kb.release(*self.kc)

    def reset(self):
        self.is_pressed = False

    def update(self, inp):
        if inp and not self.is_pressed:
            self.is_pressed = True
            if not self.is_list:
                self.kb.press(self.kc)
            else:
                self.kb.press(*self.kc)
            return self
        elif inp and self.is_pressed:
            return self
        elif not inp and not self.is_pressed:
            return self
        else:
            self.is_pressed = False
            self.release()
            return self.next_state

class KeyTapState:
    def __init__(self, name, kb, kc, next_state):
        self.name = name
        self.next_state = next_state
        self.kb = kb
        self.kc = kc
        self.kb.release(kc)

    def reset(self):
        pass

    def update(self, inp):
        self.kb.press(self.kc)
        self.kb.release(self.kc)
        return self.next_state


class WaitState:
    def __init__(self, name, T, success_state, fail_state, inverted = False):
        self.name = name
        self.T = T
        self.success_state = success_state
        self.fail_state = fail_state
        self.inverted = inverted
        self.reset()

    def reset(self):
        self.wait_started = None
        self.in_wait = None

    def update(self, inp):
        if self.inverted:
            inp = not inp
        if inp and not self.in_wait:
            self.in_wait = True
            self.wait_started = time.monotonic()
            return self
        elif inp and self.in_wait:
            if time.monotonic() - self.wait_started > self.T:
                print(f"{self.name} transitioning to success")
                return self.success_state
            return self
        elif not inp and self.in_wait:
            if time.monotonic() - self.wait_started > self.T:
                print(f"{self.name} transitioning to success")
                return self.success_state
            else:
                print(f"{self.name} transitioning to failure")
                return self.fail_state
        else:
            print("wait else?")


class StateMachine:
    def __init__(self, states):
        self.states = states
        self.reset()
        self.cur_state = states[0]

    def reset(self):
        for s in self.states:
            s.reset()

    def update(self, inp):
        next_state = self.cur_state.update(inp)
        if next_state != self.cur_state:
            print(f"State changed to {str(next_state)}")
            if next_state:
                next_state.reset()
        self.cur_state = next_state
        if self.cur_state is None:
            print("machine died, rebooting")
            self.reset()
            self.cur_state = self.states[0]
