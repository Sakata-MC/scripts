import asyncio
import struct
import sys
import socket
import threading
import queue
from datetime import datetime
from bleak import BleakClient, BleakError

# --- Configuration ---
ADDRESS = "DE:FA:55:15:81:5D"
OPENTRACK_IP = "127.0.0.1"
OPENTRACK_PORT = 4242

NOTIFY_UUID = "0000ffe4-0000-1000-8000-00805f9a34fb"
WRITE_UUID = "0000ffe9-0000-1000-8000-00805f9a34fb"

# Protocol Commands
CMD_UNLOCK     = bytearray([0xff, 0xaa, 0x69, 0x88, 0xb5])
CMD_ALGO_RESET = bytearray([0xff, 0xaa, 0x01, 0x01, 0x00])
CMD_SAVE       = bytearray([0xff, 0xaa, 0x00, 0x00, 0x00])
CMD_READ_MAG   = bytearray([0xff, 0xaa, 0x27, 0x3a, 0x00])
CMD_READ_BAT   = bytearray([0xff, 0xaa, 0x27, 0x64, 0x00])

# Thread-safe queue for UDP packets
tx_queue = queue.Queue(maxsize=10)

def udp_sender_thread():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            packet = tx_queue.get(block=True)
            if packet is None: break
            sock.sendto(packet, (OPENTRACK_IP, OPENTRACK_PORT))
        except Exception:
            pass
    sock.close()

sender = threading.Thread(target=udp_sender_thread, daemon=True)
sender.start()

def get_ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def handle_data(handle, data):
    if len(data) < 20 or data[0] != 0x55: return
    flag = data[1]
    ts = get_ts()

    # CRITICAL: Only logic inside this block results in a UDP packet
    if flag == 0x61:
        raw = struct.unpack('<hhhhhhhhh', data[2:20])
        accel = [r / 32768.0 * 16 for r in raw[0:3]]
        r, p, y = [r / 32768.0 * 180 for r in raw[6:9]]
        
        # Pack ONLY when we have 0x61 data
        packet = struct.pack('dddddd', 0.0, 0.0, 0.0, float(y), float(p), float(r))
        
        try:
            if tx_queue.full():
                tx_queue.get_nowait()
            tx_queue.put_nowait(packet)
        except queue.Full:
            pass

        sys.stdout.write(f"\033[2F[{ts}] [EULER] R:{r:>7.2f}° P:{p:>7.2f}° Y:{y:>7.2f}° | Z-Accel: {accel[2]:.2f}g\033[2E")
        sys.stdout.flush()

    elif flag == 0x71:
        reg_addr = struct.unpack('<H', data[2:4])[0]
        if reg_addr == 0x3a:
            mag = struct.unpack('<hhh', data[4:10])
            sys.stdout.write(f"\033[1F[{ts}] [MAG]   X={mag[0]:<6} Y={mag[1]:<6} Z={mag[2]:<6}\033[1E")
            sys.stdout.flush()
        elif reg_addr == 0x64 or reg_addr == 0x41:
            val = struct.unpack('<h', data[4:6])[0]
            voltage = val / 100.0
            pct = max(0, min(100, (voltage - 3.4) / (4.2 - 3.4) * 100))
            sys.stdout.write(f"\r[{ts}] [STAT]  Battery: {voltage:.2f}V ({pct:.1f}%)")
            sys.stdout.flush()

async def main():
    retries = 3
    for attempt in range(retries):
        client = BleakClient(ADDRESS)
        try:
            print(f"[{get_ts()}] Connecting (Attempt {attempt + 1})...")
            await client.connect()
            await client.write_gatt_char(WRITE_UUID, CMD_UNLOCK)
            await asyncio.sleep(0.1)
            await client.write_gatt_char(WRITE_UUID, CMD_ALGO_RESET)
            await asyncio.sleep(0.1)
            await client.write_gatt_char(WRITE_UUID, CMD_SAVE)
            
            print(f"[{get_ts()}] System Ready (Filtering for 0x61 -> {OPENTRACK_IP}:{OPENTRACK_PORT})\n\n\n")
            await client.start_notify(NOTIFY_UUID, handle_data)

            while True:
                await client.write_gatt_char(WRITE_UUID, CMD_READ_MAG)
                await asyncio.sleep(1.0)
                await client.write_gatt_char(WRITE_UUID, CMD_READ_BAT)
                await asyncio.sleep(1.0)
                
        except (OSError, BleakError) as e:
            print(f"\nConnection failed: {e}")
            if client.is_connected: await client.disconnect()
            if attempt < retries - 1: await asyncio.sleep(2.0)
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            break
        finally:
            if client.is_connected: await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        tx_queue.put(None)
        sys.stdout.write("\n\n\nStopping...\n")
