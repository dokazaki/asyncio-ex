#!/usr/bin/env python3
import argparse
import asyncio
import time
import logging
from typing import List


class MyClient:
    def __init__(self, ip: str = '127.0.0.1', port: int = 8989):
        self.log = logging.getLogger(__name__)
        self.ip = ip
        self.port = port
        self.reader = None
        self.writer = None

    async def start(self) -> None:
        print('Starting TCP client')
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)

    async def stop(self, timeout: float, tasks: List[asyncio.Task]) -> None:
        print('Start countdown to stop: {} seconds'.format(timeout))
        await asyncio.sleep(timeout)
        print('Stopping')
        self.writer.close()
        for task in tasks:
            t = await task
            self.log.info("task {} returned {}".format(task, t))

    async def writing(self) -> None:
        print('Start writing task')
        while True:
            try:
                msg = 'TCP client send at time: {}'.format(time.time())
                send_msg = '{:02d}{}'.format(len(msg), msg)
                print('TCP client sending {} to server'.format(send_msg))
                self.writer.write(send_msg.encode())
                await self.writer.drain()
                await asyncio.sleep(1.0)
            except ConnectionResetError:
                self.log.debug("writer: {} disconnected".format(self.writer))
                break
            except Exception:
                self.log.exception("problem with writer: {}".format(self.writer))
                break
        self.writer.close()

    async def reading(self) -> None:
        print('Start reading task')
        while True:
            try:
                hdr = await self.reader.read(2)
                data_len = int(hdr.decode())
                body = await self.reader.read(data_len)
                print('TCP client received {} from server'.format(body.decode()))
            except (EOFError, ValueError):
                self.log.debug("reader: {} socket closed".format(self.reader))
                break
            except Exception as e:
                self.log.exception("problem with reader: {}: {}".format(self.reader, e))
                break


if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser()
    cli_parser.add_argument('runtime', type=int, help='Number of seconds to run the client')
    args = cli_parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    client = MyClient()
    loop.run_until_complete(client.start())
    task_list = [
        asyncio.ensure_future(client.writing()),
        asyncio.ensure_future(client.reading())
    ]
    loop.run_until_complete(client.stop(args.runtime, task_list))
    loop.close()
