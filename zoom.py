import socket
import time

HOST = "127.0.0.1"
PORT = 1111

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print(sock.recv(1024))

def send(cmd):
    sock.send((cmd + "\n").encode())

# start fingers apart
send("d 0 450 500 50")
send("d 1 450 1100 50")
send("c")

time.sleep(0.05)

# balanced zoom
for i in range(7):
    y1 = 500 + i*30
    y2 = 1100 - i*30
    send(f"m 0 450 {y1} 50")
    send(f"m 1 450 {y2} 50")
    send("c")
    time.sleep(0.02)

# release fingers
send("u 0")
send("u 1")
send("c")

sock.close()