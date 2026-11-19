"""A CAN node on the inverter's CAN1 (default canspeed 500 kbit/s). It only listens and logs: the inverter sends nothing
until the terminal maps parameters to CAN ids (term_peer.py maps fstat to 0x180 and amp to 0x181, every 100 ms)."""
class Node:
    def __init__(self, ctx):
        self.ctx = ctx

    def on_frame(self, f):
        self.ctx.info(f"CAN RX id=0x{f['id']:X} data={bytes(f['data']).hex()}")
