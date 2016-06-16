#!/usr/bin/env python
import asyncio
import logging
import time
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
        self.stop_event = asyncio.Event()  # Windows doesn't do signals, so use a queue
        self.clients = []
        self.tasks = set()

    async def handle_client(self, reader, writer):
        task = asyncio.ensure_future(self.process_client(reader, writer))
        self.tasks.add(task)

    async def process_client(self, reader, writer):
        """ Handle socket I/O for one TCP client - persist until client closes connection or until server shutdown """
        print('Client handler started for socket {}'.format(writer.get_extra_info('peername')))
        self.clients.append(writer)
        while True:
            try:
                hdr = await reader.readexactly(2)
                data_len = int(hdr.decode())
                body = await reader.read(data_len)
            except EOFError:
                self.log.debug("reader %s gone", reader)
                break
            except Exception:
                self.log.exception("problem with %s", reader)
                break

            print('Got request: {}'.format(body))

            item = ServiceCall(writer, body)
            print('Client request received')
            await asyncio.sleep(0.5)
            print('Client echo response being sent')
            try:
                item.writer.write(item.payload)
                await item.writer.drain()
            except ConnectionResetError:
                self.log.debug("writer %s gone", writer)
                break
            except Exception:
                self.log.exception("problem with %s", writer)
                break
        writer.close()

    async def alert_generator(self):
        """ Send alerts at random intervals """
        print('Alert generator started to send messages to all clients')
        while self.stop_event.is_set():
            await asyncio.sleep(random() * 5.0)
            msg_body = 'Alert: {}'.format(time.time())
            msg = '{:02d}{}'.format(len(msg_body.encode()), msg_body)
            payload = msg.encode()
            print('Sending alert: {}'.format(msg))
            failed_clients = set()
            for client in self.clients:
                try:
                    client.write(payload)
                except Exception:
                    self.log.exception("problem writing alert")
                    failed_clients.add(client)
            for client in self.clients:
                try:
                    await client.drain()
                except Exception:
                    self.log.exception("problem waiting for client to drain")
                    failed_clients.add(client)
            if len(failed_clients):
                self.log.info("dropping %d client(s)", len(failed_clients))
                self.clients = [c for c in self.clients if c not in failed_clients]

    async def start(self):
        print('Starting TCP server')
        self.server = await asyncio.start_server(self.handle_client, self.ip, self.port)
        print('Server started on {}:{}'.format(self.ip, self.port))

    async def stop(self, wait_time: float):
        """ Initiates server shutdown by writing to the sigstop queue """
        print('Will stop server after {} seconds runtime'.format(wait_time))
        await asyncio.sleep(wait_time)
        self.stop_event.set()

    async def kill(self):
        """ Shutdown the server when the stop_event is set """
        print('Waiting to receive signal to stop server')
        await self.stop_event.wait()
        print('Received signal to stop the server')
        self.server.close()
        for client in self.clients:
            client.close()
        for task in self.tasks:
            t = await task
            self.log.info("task %s returned %s", task, t)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    server = MyServer()
    loop.run_until_complete(server.start())
    for t in [
            server.stop(6.0),
            server.alert_generator()
    ]:
        task = asyncio.ensure_future(t)
        server.tasks.add(task)
    loop.run_until_complete(server.kill())
    loop.close()
