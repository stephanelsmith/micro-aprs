
from machine import Pin
from micropython import const

from .defs import PD

class SA868Pwr():
    def __init__(self):
		self.sa868_pd   = Pin(PD, Pin.OUT)
		self.sa868_pd.value(0)

    async def start(self):
		self.sa868_pd.value(1)

    async def stop(self, verbose=False):
		self.sa868_pd.value(0)

    async def __aenter__(self):
        try:
            await self.start()
        except:
            await self.stop()
            raise
        return self

    async def __aexit__(self, *args):
        await self.stop()

