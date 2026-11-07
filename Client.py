#!/usr/bin/env python3
"""Continuous Berkeley clock synchronization client (simulation only)."""

import argparse
import json
import socket
import threading
import time


def send_message(sock, message):
    sock.sendall((json.dumps(message) + "\n").encode("utf-8"))


def send_clock_reports(sock, interval, stop):
    while not stop.is_set():
        try:
            send_message(sock, {"type": "time", "timestamp": time.time()})
        except OSError:
            stop.set()
            return
        if stop.wait(interval):
            return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server_ip", help="LAN IP address of the coordinator computer")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between clock reports; match the server interval")
    args = parser.parse_args()
    if not 0.1 <= args.interval <= 3600:
        parser.error("--interval must be between 0.1 and 3600 seconds")

    stop = threading.Event()
    try:
        with socket.create_connection((args.server_ip, args.port), timeout=15) as sock:
            sock.settimeout(None)
            print(f"Connected to {args.server_ip}:{args.port}; reporting every {args.interval:g}s", flush=True)
            sender = threading.Thread(target=send_clock_reports, args=(sock, args.interval, stop), daemon=True)
            sender.start()
            stream = sock.makefile("r", encoding="utf-8")
            try:
                for line in stream:
                    try:
                        result = json.loads(line)
                        if result.get("type") != "adjustment":
                            print("Ignored an unexpected server message.", flush=True)
                            continue
                        correction = float(result["correction_seconds"])
                        adjusted = float(result["adjusted_timestamp"])
                    except (json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError):
                        print("Ignored an invalid synchronization response.", flush=True)
                        continue
                    print(
                        f"Simulated synchronized time: {time.ctime(adjusted)} "
                        f"(correction {correction:+.3f}s; system clock unchanged)",
                        flush=True,
                    )
            finally:
                stop.set()
                stream.close()
        print("Server disconnected.", flush=True)
    except (OSError, UnicodeError) as exc:
        parser.exit(1, f"Could not complete synchronization: {exc}\n")
    except KeyboardInterrupt:
        stop.set()
        print("\nClient stopped.", flush=True)


if __name__ == "__main__":
    main()
