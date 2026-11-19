"""Serial terminal on USART3 (115200 8N2), scripted: polls the parameters in POLL with one `get` every POLL_MS.
The firmware echoes the command and prints one value per line; plot.py turns those lines back into columns."""
POLL = "opmode,status,fstat,amp,ampnom,fslipspnt,cpuload"
POLL_MS = 100
# The F103 ADC has no analog input in this sim build, so udc and the throttle read 0: lower the udc thresholds, and pick the
# operating point with motor parameters instead of a throttle (boost = voltage at 0 Hz in dig, fslipmin = slip frequency at 0 % throttle).
SETUP = [(0.20, "set udcsw 0"), (0.25, "set udcmin 0"), (0.30, "set boost 10000"), (0.35, "set fslipmin 5"),
         (0.40, "can tx fstat 384 0 16 1"), (0.45, "can tx amp 385 0 16 1")]   # CAN TX map: 0x180 = fstat, 0x181 = amp, both sent every 100 ms

class Peer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.n = 0
        ctx.schedule_periodic_ns(10_000_000)

    def on_timer(self):
        self.n += 1
        t = self.n * 0.010
        for at, cmd in SETUP:
            if abs(t - at) < 0.005:
                self.ctx.send((cmd + "\n").encode())
        if t >= 0.5 and self.n % (POLL_MS // 10) == 0:
            self.ctx.send(("get " + POLL + "\n").encode())

    def on_byte(self, b):
        pass
