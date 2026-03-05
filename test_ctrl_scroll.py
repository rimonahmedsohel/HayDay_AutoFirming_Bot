import socket
import time

HOST = "127.0.0.1"
PORT = 1111

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

print(s.recv(1024))

commands = [
    "d 0 450 800 50\n",
    "d 1 450 800 50\n",
    "c\n",

    "m 0 450 600 50\n",
    "m 1 450 1000 50\n",
    "c\n",

    "u 0\n",
    "u 1\n",
    "c\n"
]

for cmd in commands:
    s.send(cmd.encode())
    time.sleep(0.02)

s.close()