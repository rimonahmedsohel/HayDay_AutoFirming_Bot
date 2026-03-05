import socket
import time

HOST = "127.0.0.1"
PORT = 1111

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print(sock.recv(1024))

def send(cmd):
    sock.send((cmd + "\n").encode())


def zoom_out(level=0.7):

    # clamp level between 0 and 1
    level = max(0.1, min(level, 1.0))

    center_x = 450
    center_y = 800

    start_offset = int(250 * level)
    step = int(30 * level)
    steps = int(6 + 4 * level)

    y1_start = center_y - start_offset
    y2_start = center_y + start_offset

    send(f"d 0 {center_x} {y1_start} 50")
    send(f"d 1 {center_x} {y2_start} 50")
    send("c")

    time.sleep(0.05)

    for i in range(steps):
        y1 = y1_start + i * step
        y2 = y2_start - i * step
        send(f"m 0 {center_x} {y1} 50")
        send(f"m 1 {center_x} {y2} 50")
        send("c")
        time.sleep(0.02)

    send("u 0")
    send("u 1")
    send("c")


# Example usage
zoom_out(0.65)

sock.close()