#!/usr/bin/env python3
"""Continuous Berkeley clock synchronization coordinator (simulation only)."""

import argparse
import json
import socket
import threading
import time


def send_message(conn, message):
    conn.sendall((json.dumps(message) + "\n").encode("utf-8"))


def receive_client(conn, address, clients, lock):
    """Read newline-delimited clock reports until this client disconnects."""
    stream = conn.makefile("r", encoding="utf-8")
    try:
        for line in stream:
            try:
                message = json.loads(line)
                timestamp = message.get("timestamp")
                if message.get("type") != "time" or not isinstance(timestamp, (int, float)):
                    print(f"Ignored invalid clock report from {address[0]}:{address[1]}", flush=True)
                    continue
            except json.JSONDecodeError:
                print(f"Ignored invalid message from {address[0]}:{address[1]}", flush=True)
                continue
            with lock:
                client = clients.get(conn)
                if client is not None:
                    client["timestamp"] = float(timestamp)
                    client["received_at"] = time.monotonic()
    except (ConnectionError, OSError, UnicodeError):
        pass
    finally:
        with lock:
            clients.pop(conn, None)
        try:
            stream.close()
        except OSError:
            pass
        conn.close()
        print(f"Client {address[0]}:{address[1]} disconnected", flush=True)


def synchronize(clients, lock, interval):
    """Periodically calculate the mean offset and send a shared virtual time."""
    while True:
        time.sleep(interval)
        coordinator_time = time.time()
        monotonic_now = time.monotonic()
        max_age = max(interval * 3, 15)
        with lock:
            active = [
                (conn, info.copy())
                for conn, info in clients.items()
                if info["timestamp"] is not None
                and monotonic_now - info["received_at"] <= max_age
            ]

        if not active:
            print("No recent client clocks; waiting for reports.", flush=True)
            continue

        offsets = [info["timestamp"] - coordinator_time for _, info in active]
        average_offset = sum(offsets) / (len(offsets) + 1)  # Include the coordinator's zero offset.
        shared_time = coordinator_time + average_offset
        print(
            f"\nSync cycle: {len(active)} client(s); average adjustment {average_offset:+.3f}s; "
            f"shared time {time.ctime(shared_time)}",
            flush=True,
        )

        for (conn, info), offset in zip(active, offsets):
            correction = average_offset - offset
            try:
                send_message(conn, {
                    "type": "adjustment",
                    "correction_seconds": correction,
                    "adjusted_timestamp": shared_time,
                    "average_adjustment_seconds": average_offset,
                })
                print(f"  {info['address'][0]}: correction {correction:+.3f}s", flush=True)
            except (BrokenPipeError, ConnectionError, OSError):
                # The receive thread will remove the disconnected client.
                continue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="address to listen on (default: all network interfaces)")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between synchronization cycles")
    args = parser.parse_args()
    if not 0.1 <= args.interval <= 3600:
        parser.error("--interval must be between 0.1 and 3600 seconds")

    clients = {}
    lock = threading.Lock()
    sync_thread = threading.Thread(target=synchronize, args=(clients, lock, args.interval), daemon=True)
    sync_thread.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(100)
        print(
            f"Berkeley coordinator listening on {args.host}:{args.port}; "
            f"sync interval {args.interval:g}s (system clock unchanged)",
            flush=True,
        )
        try:
            while True:
                conn, address = server.accept()
                conn.settimeout(None)
                with lock:
                    clients[conn] = {"address": address, "timestamp": None, "received_at": 0.0}
                print(f"Client {address[0]}:{address[1]} connected", flush=True)
                threading.Thread(
                    target=receive_client,
                    args=(conn, address, clients, lock),
                    daemon=True,
                ).start()
        except KeyboardInterrupt:
            print("\nServer stopped.", flush=True)


if __name__ == "__main__":
    main()
