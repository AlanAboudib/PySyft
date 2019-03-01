import time
import asyncio
import websockets
import syft as sy
from syft.serde import serialize
from syft.workers.base import BaseWorker
import torch
class FLClientWorker(BaseWorker):
    def __init__(
        self, hook, id=0, known_workers={}, is_client_worker=False,
        log_msgs=False, verbose=False, connection_params={}, data={}
        ):
        # TODO get angry when we have no connection params
        self.port = connection_params['port']
        self.host = connection_params['host']
        self.current_status = 'ready'
        self.connections = set()
        self.msg_queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop()
        self.uri = f'ws://{self.host}:{self.port}'
        super().__init__(hook, id, known_workers, is_client_worker, log_msgs, verbose)
        self.start()

    def msg(self, msg):
        return f'[{self.id}] {msg}'

    def worker_metadata(self):
        return [ obj.shape for key, obj in self.worker._objects.items() ]

    async def consumer_handler(self, websocket):
        while True:
            if not websocket.open:
                websocket = await websockets.connect(self.uri)
            msg = await websocket.recv()
            print(f'[{self.id} | RCV] {msg}')
            await self.msg_queue.put(msg)


    async def producer_handler(self, websocket):
        while True:
            msg = await self.msg_queue.get()
            if msg == 'STAT':
                await websocket.send(self.msg(self.current_status))
            if msg == 'META':
                await websocket.send(self.msg(self.worker_metadata()))
            if msg == 'GIMME_DATA':
                await websocket.send(serialize(self.worker._objects))

    async def handler(self, websocket):
        asyncio.set_event_loop(self.loop)
        consumer_task = asyncio.ensure_future(self.consumer_handler(websocket))
        producer_task = asyncio.ensure_future(self.producer_handler(websocket))

        done, pending = await asyncio.wait([consumer_task, producer_task]
                                        , return_when=asyncio.FIRST_COMPLETED)
        print("Connection closed, canceling pending tasks")
        for task in pending:
            task.cancel()

    async def connect(self):
        async with websockets.connect(self.uri) as websocket:
            while True:
                if not websocket.open:
                    websocket = await websockets.connect(self.uri)
                await self.handler(websocket)

    def start(self):
        asyncio.get_event_loop().run_until_complete(self.connect())
        print("Starting client..\n")




    def _send_msg(self, message, location):
        return location._recv_msg(message)

    def _recv_msg(self, message):
        return self.recv_msg(message)

