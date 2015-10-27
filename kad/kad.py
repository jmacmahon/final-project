from multiprocessing import Pipe, Process
from time import sleep

SLEEP_TIME = 0.1
DEBUG = True

class DebugConnection(object):
    def __init__(self, connection):
        self.connection = connection
        self.thisEndName = 'unnamed'
        self.otherEndName = 'unnamed'

    def send(self, obj):
        print('Send: %s -> %s: %s' %
              (self.thisEndName, self.otherEndName, repr(obj)))
        return self.connection.send(obj)

    def recv(self):
        obj = self.connection.recv()
        print('Recv: %s <- %s: %s' %
              (self.thisEndName, self.otherEndName, repr(obj)))
        return obj

def setConnectionNames(left, right, leftName, rightName):
    left.thisEndName = right.otherEndName = leftName
    right.thisEndName = left.otherEndName = rightName

def DebugPipe(duplex=True):
    parent, child = Pipe(duplex=duplex)
    return DebugConnection(parent), DebugConnection(child)

class Node(object):
    def __call__(self, managerPipe):
        self.managerPipe = managerPipe
        self.managerPipe.send('running')
        self.pid = self.managerPipe.recv()
        if DEBUG:
            managerPipe.thisEndName = str(self.pid)

        self._run()

    def _run(self):
        pass

class EchoNode(Node):
    def _run(self):
        end = False
        while not end:
            data = self.managerPipe.recv()
            if data == 'end':
                end = True
            self.managerPipe.send(data)

class SingleConnectionNode(Node):
    def _run(self):
        self.connections = {}
        end = False
        while not end:
            # Check Manager
            if self.managerPipe.poll():
                self.handleManager(self.managerPipe.recv())
            # Check connections
            for pid, pipe in self.connections.items():
                if pipe.poll():
                    self.handle(pid, pipe.recv())
            sleep(SLEEP_TIME)

    def handle(self, pid, data):
        pass

    def handleManager(self, data):
        pass

class Manager(object):
    def __init__(self):
        self.nodes = {}

    def newNode(self, nodeClass, *args, **kwargs):
        if DEBUG:
            parentPipe, childPipe = DebugPipe()
            setConnectionNames(parentPipe, childPipe,
                               'manager', 'new child')
        else:
            parentPipe, childPipe = Pipe()

        process = Process(target=nodeClass(*args, **kwargs),
                          args=(childPipe,))
        process.parentPipe = parentPipe
        process.start()
        assert parentPipe.recv() == 'running', 'Node unresponsive'
        if DEBUG:
            setConnectionNames(parentPipe, childPipe,
                               'manager', str(process.pid))
        parentPipe.send(process.pid)
        self.nodes[process.pid] = process
