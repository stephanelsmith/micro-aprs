
import asyncio
from micropython import const

from machine import UART
from machine import Pin

class SA868():
    def __init__(self, ):
        self.uart = None

    async def start(self):
        self.uart = UART(1, 9600, tx=_SA868_RX, rx=_SA868_TX)

    async def stop(self, verbose=False):
        pass

    async def __aenter__(self):
        try:
            await self.start()
        except:
            await self.stop()
            raise
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def rx_coro(self):
        pass
    async def tx_coro(self):
        pass

