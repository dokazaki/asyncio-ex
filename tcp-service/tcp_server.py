#!/usr/bin/env python
import asyncio
import logging
import time
from typing import List
from random import random


class ServiceCall:
    """ Instantiate per socket client request, store writer to identify where to send response """
    def __init__(self, writer: asyncio.StreamWriter, data: bytes):
        self.writer_stream = writer
        payload_str = '{:02d}{}'.format(len(data), data.decode())
        self.payload_data = payload_str.encode()

    @property
    def payload(self) -> bytes:
        return self.payload_data

    @property
    def writer(self) -> asyncio.StreamWriter:
        if self.writer_stream.get_extra_info('peername') is None:
            return None
        else:
            return self.writer_stream


class MyServer:
    def __init__(self, ip: str = '127.0.0.1', port: int = 8989):
        self.log = logging.getLogger(__name__)
        self.ip = ip
        self.port = port
        self.server = None
        self.in_queue = asyncio.Queue()
        self.sigstop_queue = asyncio.Queue(maxsize=1)  # Windows doesn't do signals, so use a queue
        self.clients = []

    async def handle_client(self, reader, writer):
        """ Handle socket I/O for one TCP client - persist until client closes connection or until server shutdown """
        print('Client handler started for socket {}'.format(writer.get_extra_info('peername')))
        self.clients.append(writer)
        while True and writer.get_extra_info('peername') is not None:
            try:
                hdr = await reader.read(2)
                data_len = int(hdr.decode())
                body = await reader.read(data_len)
            except ConnectionResetError as e:
                self.log.info("Socket closed: {}".format(e))
                return
            except ValueError as e:
                self.log.info("Client sent EOF: {}".format(e))
                return

            print('Got request: {}'.format(body))
            q_data = ServiceCall(writer, body)
            await self.in_queue.put(q_data)
        writer.close()

    async def responder(self):
        """ Sit on input Q, and copy Q items to originating socket after a slight delay """
        print('Responder started for handling queued items')
        while True:
            item = await self.in_queue.get()
            print('Client request received')
            await asyncio.sleep(0.5)
            if item.writer.get_extra_info('peername') is not None:
                print('Client echo response being sent')
                item.writer.write(item.payload)
                await item.writer.drain()
            else:
                self.log.info("Client socket closed before response could be sent")
            self.in_queue.task_done()

    async def alert_generator(self):
        """ Send alerts at random intervals """
        print('Alert generator started to send messages to all clients')
        while True:
            await asyncio.sleep(random() * 5.0)
            msg_body = 'Alert: {}'.format(time.time())
            msg = '{:02d}{}'.format(len(msg_body.encode()), msg_body)
            payload = msg.encode()
            print('Sending alert: {}'.format(msg))
            for client in self.clients:
                client.write(payload)
                await client.drain()

    async def start(self):
        print('Starting TCP server')
        self.server = await asyncio.start_server(self.handle_client, self.ip, self.port)
        print('Server started on {}:{}'.format(self.ip, self.port))

    async def stop(self, wait_time: float):
        """ Initiates server shutdown by writing to the sigstop queue """
        print('Will stop server after {} seconds runtime'.format(wait_time))
        await asyncio.sleep(wait_time)
        await self.sigstop_queue.put('1')

    async def kill(self, tasks: List[asyncio.Task]):
        """ Shutdown the server when anything is received in the sigstop queue """
        print('Waiting to receive signal to stop server')
        await self.sigstop_queue.get()
        print('Received signal to stop the server')
        for task in tasks:
            task.cancel()
        self.sigstop_queue.task_done()
        self.server.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    server = MyServer()
    loop.run_until_complete(server.start())
    task_list = [
        asyncio.ensure_future(server.stop(60.0)),
        asyncio.ensure_future(server.responder()),
        asyncio.ensure_future(server.alert_generator())
    ]
    loop.run_until_complete(server.kill(task_list))
    loop.close()
