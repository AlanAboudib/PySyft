import time
import os
import asyncio
import websockets
from multiprocessing import Process
from collections import ChainMap

import numpy as np
import torch
import torch.utils.data as data
from torchvision import datasets, transforms
from torchvision.datasets.mnist import MNIST
import syft as sy

from federated_learning_server import FederatedLearningServer
from federated_learning_client import FederatedLearningClient

from fl_server_worker import FLServerWorker
from fl_client_worker import FLClientWorker

def data_transforms():
    return transforms.Compose([
                        transforms.ToTensor(),
                        transforms.Normalize((0.1307,), (0.3081,))
                    ])

def build_datasets():
    train = datasets.MNIST('../data', train=True, download=True, transform=data_transforms())
    test = datasets.MNIST('../data', train=False, transform=data_transforms())
    return train, test


def start_proc(participant, kwargs):
    """ helper function for spinning up a websocket participant """
    def target():
        server = participant(**kwargs)
        #server.start()
    p = Process(target=target)
    p.start()
    return p

async def repl(uri='ws://localhost:8765'):
    async with websockets.connect(uri) as websocket:
        while True:
            if not websocket.open:
                websocket = await websockets.connect(uri)
            cmd = input("\ncmd:  ")
            await websocket.send(cmd)
            resp = await websocket.recv()
            print("<REPL> {}".format(resp))

def xxxmain():
    hook = sy.TorchHook(torch)
    kwargs = { "id": "fed1", "connection_params": { 'host': 'localhost', 'port': 8765 }, "hook": hook }
    server = start_proc(FederatedLearningServer, kwargs)
    time.sleep(1)
    t = torch.ones(5)
    worker_args = ChainMap({ 'id': f'bobby', 'data': (t) }, kwargs)
    client = start_proc(FederatedLearningClient, worker_args)
    time.sleep(1)

def main():
    hook = sy.TorchHook(torch)
    kwargs = { "id": "fed1", "connection_params": { 'host': 'localhost', 'port': 8765 }, "hook": hook }
    server = start_proc(FLServerWorker, kwargs)

    time.sleep(1)
    t = torch.ones(5)
    worker_args = ChainMap({ 'id': f'bobby', 'data': (t) }, kwargs)
    client = start_proc(FLClientWorker, worker_args)
    time.sleep(1)


"""
    How to setup FL environment
"""
# host python clients
# define how clients connect to server
# define how data goes into the worker
# define the model
#    (a) - we send the entire model params +  the training plan
#        - at we define the model as a class (msgpack, protobuf)
#    (b) - we send the entire model params +  the training plan
#        - we perform every instruction using workers (notebooks)

if __name__ == "__main__":
    main()
