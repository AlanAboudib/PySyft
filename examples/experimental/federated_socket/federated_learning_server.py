import time
import asyncio
import websockets
import syft as sy
import msgpack
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch import nn
from torch import optim
from syft.serde import serialize
class Net(nn.Module):
    """ standard LeCun net """
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 20, 5, 1)
        self.conv2 = nn.Conv2d(20, 50, 5, 1)
        self.fc1 = nn.Linear(4*4*50, 500)
        self.fc2 = nn.Linear(500, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 4*4*50)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)

def train(model, device, train_loader, optimizer, epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(epoch, batch_idx * len(data), len(train_loader.dataset),
            100. * batch_idx / len(train_loader), loss.item()))




class FederatedLearningServer:
    def __init__(self, id, connection_params, hook, loop=None):
        self.port = connection_params['port']
        self.host = connection_params['host']
        self.id = id
#        self.worker = sy.VirtualWorker(hook, id=id, verbose=True)
        self.current_status = 'waiting_for_clients'
        self.connections = set()
        self.broadcast_queue = asyncio.Queue()
        self.loop = asyncio.new_event_loop() if loop is None else loop
        self.model = Net()

    def msg(self, msg):
        return f'[{self.id}] {msg}'

    def serialized_model(self):
        """ this needs to change """
        print(self.model.state_dict())
        return serialize(list(self.model.state_dict().values())[0])

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
                if message == 'STAT':
                    await ws.send(self.msg(self.current_status))
                    await ws.send('STAT')
                if message == 'META':
                    await ws.send('META')
                if message == 'START_TRAINING_ROUND':
                    pass
"""
                    f0
                    w0 t_1 = tensorA()
                    w0 t_2 = tensorB()
                    foobar = t_1 @ t_2
SEARCH xs
ptr
deserialize and store in my websocket_worker



f0: t_1, t_2 => @
w0:


f0: @w0, give pointers to all @w0._objects
f0: iterate on first dim of xs, ys
f0: ptr = model.send(@w0)
w0: registers model and stores it locally
f0: ptr(xs_t)

"""

#                    self.model.send(
#                    await ws.send(f'CUR_MODEL {self.serialized_model()}')

    async def handler(self, websocket, path):
        cid = len(self.connections)
        await websocket.send(f'Welcome {cid}')
        self.connections.add(websocket)
        asyncio.set_event_loop(self.loop)
        consumer_task = asyncio.ensure_future(self.consumer_handler(websocket, cid))
        producer_task = asyncio.ensure_future(self.producer_handler(websocket, cid))

        done, pending = await asyncio.wait([consumer_task, producer_task] , return_when=asyncio.FIRST_COMPLETED)
        print("Connection closed, canceling pending tasks")
        for task in pending:
            task.cancel()


    def start(self):
        start_server = websockets.serve(self.handler, self.host, self.port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
        print("Starting Federator...\n")

