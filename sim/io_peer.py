"""Scripted driver/vehicle inputs on digital pads (not a plant: fixed switch positions at fixed times).
Outputs, in order: PC7 emergency-stop loop (high = closed), PA4 forward select, PB6 start (key)."""
EVENTS = [(0, 0, 1), (0.4, 1, 1), (0.8, 2, 1)]   # (seconds, output index, level)

class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self.todo = sorted(EVENTS)
        self._arm()

    def _arm(self):
        if self.todo:
            self.ctx.schedule_oneshot_ns(max(1, int(self.todo[0][0] * 1e9) - self.ctx.now_ns))

    def on_timer(self):
        while self.todo and int(self.todo[0][0] * 1e9) <= self.ctx.now_ns:
            _, i, lvl = self.todo.pop(0)
            self.ctx.gpio(i).set(bool(lvl))
        self._arm()

    def on_gpio(self, line, level):
        pass
