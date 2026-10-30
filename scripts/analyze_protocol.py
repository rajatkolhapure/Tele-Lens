import os
import re

def analyze_symbols_and_network(so_path, dll_path):
    print("=== Analyzing Android libnative-lib.so ===")
    with open(so_path, 'rb') as f:
        so_data = f.read()

    # Find format strings, sockets, ports
    print("\n--- Network / Protocol Strings in libnative-lib.so ---")
    matches = re.findall(rb'[a-zA-Z0-9_\-\./:%]{4,}', so_data)
    decoded = [m.decode('latin-1') for m in matches]
    for s in decoded:
        if any(k in s.lower() for k in ["469", "tcp", "udp", "port", "socket", "ack", "packet", "nalu", "sps", "pps", "send", "recv", "connect", "listen", "accept", "h264", "hevc", "video"]):
            if len(s) < 80 and not s.startswith("Landroid") and not s.startswith("org/"):
                print("  ", s)

    print("\n=== Analyzing Windows engine.dll ===")
    with open(dll_path, 'rb') as f:
        dll_data = f.read()

    print("\n--- Network / Protocol Strings in engine.dll ---")
    matches = re.findall(rb'[a-zA-Z0-9_\-\./:%]{4,}', dll_data)
    decoded = [m.decode('latin-1') for m in matches]
    for s in decoded:
        if any(k in s.lower() for k in ["469", "tcp", "udp", "port", "socket", "ack", "packet", "nalu", "sps", "pps", "send", "recv", "connect", "listen", "accept", "h264", "hevc", "video", "driver", "directshow", "yuv", "nv12"]):
            if len(s) < 80:
                print("  ", s)

analyze_symbols_and_network("scratch_iriun/apk/lib/arm64-v8a/libnative-lib.so", "scratch_iriun/win/engine.dll")
