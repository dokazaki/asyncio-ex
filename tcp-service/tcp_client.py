#!/usr/bin/env python
import asyncio
import time
import logging
from typing import List


class MyClient:
    def __init__(self, ip: str = '127.0.0.1', port: int = 8989):
        self.ip = ip
        self.port = port
        self.reader = None
        self.writer = None

    async def start(self):
        print('Starting TCP client')
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)

    async def stop(self, timeout: float, tasks: List[asyncio.Task]):
        print('Start countdown to stop: {} seconds'.format(timeout))
        await asyncio.sleep(timeout)
        print('Stopping')
        self.writer.close()
        for task in tasks:
            task.cancel()

    async def writing(self):
        print('Start writing task')
        while self.writer.get_extra_info('peername') is not None:
            msg = 'TCP client send at time: {}'.format(time.time())
            send_msg = '{:02d}{}'.format(len(msg), msg)
            print('TCP client sending {} to server'.format(send_msg))
            self.writer.write(send_msg.encode())
            await self.writer.drain()
            await asyncio.sleep(3.0)

    async def reading(self):
        print('Start reading task')
        while self.writer.get_extra_info('peername') is not None:
            hdr = await self.reader.read(2)
            data_len = int(hdr.decode())
            body = await self.reader.read(data_len)
            print('TCP client received {} from server'.format(body.decode()))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    client = MyClient()
    loop.run_until_complete(client.start())
    task_list = [
        asyncio.ensure_future(client.writing()),
        asyncio.ensure_future(client.reading())
    ]
    loop.run_until_complete(client.stop(20.0, task_list))
    loop.close()
