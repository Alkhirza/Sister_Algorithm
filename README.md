# Berkeley Clock Synchronization Demo

A Python TCP demo of the Berkeley clock synchronization algorithm. The server gathers clock readings from connected clients, computes an average adjustment including its own clock, and periodically sends a shared simulated adjusted time. It displays synchronization results and **does not change system clocks**.

## Run on the same LAN

1. On the coordinator computer, find its LAN IP address (Linux: `hostname -I`; Windows: `ipconfig`; macOS: **System Settings → Network**).
2. Start the server. Set the synchronization interval in seconds if you want something other than the 5-second default:

   ```bash
   python3 Server.py --interval 5
   ```

   The server listens on all network interfaces at port `5000` by default and accepts multiple clients.
3. On each client computer, run:

   ```bash
   python3 Client.py 192.168.1.25 --interval 5
   ```

   Replace `192.168.1.25` with the coordinator’s LAN IP. Keep the client interval the same as the server interval. All clients must use the same port as the server; pass `--port PORT` to either program to change it.
4. If clients cannot connect, allow inbound TCP port `5000` through the coordinator’s firewall and check that Wi-Fi client isolation is disabled. Do not expose the port to the public internet for this LAN demo.

Use Python 3. No third-party packages are required. Start the server before the clients. The server reports each synchronization cycle; press `Ctrl+C` to stop it. Press `Ctrl+C` on a client to disconnect it. The average ignores clients whose latest report is more than three intervals old (with a 15-second minimum). This simple teaching demo does not compensate for network delay, so it is not suitable for precision timekeeping.
