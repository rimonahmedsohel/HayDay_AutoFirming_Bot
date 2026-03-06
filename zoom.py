import socket
import time
import subprocess

HOST = "127.0.0.1"
PORT = 1111
DEVICE = "127.0.0.1:7555"


def ensure_minitouch():
    print("[ZOOM] Checking if minitouch is running...")
    
    # Always ensure port forward is established first
    subprocess.run(
        f"adb -s {DEVICE} forward tcp:1111 localabstract:minitouch",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test.settimeout(2.0)
        test.connect((HOST, PORT))
        data = test.recv(1024)
        test.close()
        
        if data:
            print("[ZOOM] minitouch is already running.")
            return
    except Exception as e:
        pass

    print("[ZOOM] minitouch not active. Starting in a new terminal...")

    import os
    creationflags = 0
    if hasattr(subprocess, 'CREATE_NEW_CONSOLE'):
        creationflags |= subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(
        f"adb -s {DEVICE} shell /data/local/tmp/minitouch",
        shell=True,
        creationflags=creationflags
    )

    time.sleep(2)


def send(sock, cmd):
    sock.send((cmd + "\n").encode())


def zoom_out(level=0.7):

    ensure_minitouch()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    print(sock.recv(1024))

    level = max(0.1, min(level, 1.0))

    center_x = 450
    center_y = 800

    start_offset = int(250 * level)
    step = int(30 * level)
    steps = int(6 + 4 * level)

    y1_start = center_y - start_offset
    y2_start = center_y + start_offset

    send(sock, f"d 0 {center_x} {y1_start} 50")
    send(sock, f"d 1 {center_x} {y2_start} 50")
    send(sock, "c")

    time.sleep(0.05)

    for i in range(steps):
        y1 = y1_start + i * step
        y2 = y2_start - i * step
        send(sock, f"m 0 {center_x} {y1} 50")
        send(sock, f"m 1 {center_x} {y2} 50")
        send(sock, "c")
        time.sleep(0.02)

    send(sock, "u 0")
    send(sock, "u 1")
    send(sock, "c")

    sock.close()


# Example usage
zoom_out(0.65)