import time
import torch
import asyncio
import websockets
import syft as sy
from syft.serde import serialize
from syft.workers.base import BaseWorker
class FLServerWorker(BaseWorker):
    def __init__(
        self, hook, id=0, known_workers={}, is_client_worker=False,
        log_msgs=False, verbose=False, connection_params={}, data={}
        ):
        # TODO get angry when we have no connection params
        self.port = connection_params['port']
        self.host = connection_params['host']
        self.current_status = 'waiting_for_clients'
        self.connections = set()
        self.broadcast_queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop()

        super().__init__(hook, id, known_workers, data, is_client_worker, log_msgs, verbose)
        self.start()


    def _send_msg(self, message, location):
        return location._recv_msg(message)

    def _recv_msg(self, message):
        return self.recv_msg(message)


    def msg(self, msg):
        return f'[{self.id}] {msg}'

    async def consumer_handler(self, websocket, cid):
        while True:
            msg = await websocket.recv()
            print(f'[{self.id} | RCV] {msg}')
            await self.broadcast_queue.put(msg)


    async def producer_handler(self, websocket, cid):
        while True:
            print("Waiting for message in queue")
            message = await self.broadcast_queue.get()

            for idx, ws in enumerate(self.connections):
                if message == '[bobby] ready':
                    await ws.send('GIMME_DATA')
                if message == 'STAT':
                    await ws.send(self.msg(self.current_status))
                    await ws.send('STAT')
                if message == 'META':
                    await ws.send('META')
                if message == 'START_TRAINING_ROUND':
                    pass


    async def handler(self, websocket, path):
        cid = len(self.connections)
        await websocket.send(f'Welcome {cid}')
        self.connections.add(websocket)
        asyncio.set_event_loop(self.loop)
        consumer_task = asyncio.ensure_future(self.consumer_handler(websocket, cid))
        producer_task = asyncio.ensure_future(self.producer_handler(websocket, cid))
        await websocket.send(f'STAT')

        done, pending = await asyncio.wait([consumer_task, producer_task] , return_when=asyncio.FIRST_COMPLETED)
        print("Connection closed, canceling pending tasks")
        for task in pending:
            task.cancel()

    def start(self):
        print("Starting Federator...\n")
        start_server = websockets.serve(self.handler, self.host, self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

