import os
import re
import struct

def extract_strings(file_path, min_len=4):
    with open(file_path, 'rb') as f:
        data = f.read()
    ascii_strings = re.findall(rb'[ -~]{' + str(min_len).encode() + rb',}', data)
    wide_strings = re.findall(rb'(?:[ -~]\x00){' + str(min_len).encode() + rb',}', data)
    decoded = [s.decode('latin-1') for s in ascii_strings]
    for w in wide_strings:
        try:
            decoded.append(w.decode('utf-16le'))
        except:
            pass
    return decoded

def search_patterns(strings, keywords):
    results = {}
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        matches = [s for s in strings if pattern.search(s)]
        results[kw] = matches[:20]  # top 20
    return results

print("=== Analyzing Iriun Windows files ===")
win_exe = "scratch_iriun/win/IriunWebcam.exe"
win_engine = "scratch_iriun/win/engine.dll"

for path in [win_exe, win_engine]:
    if os.path.exists(path):
        strs = extract_strings(path)
        print(f"\n--- {path} (total strings: {len(strs)}) ---")
        kw_results = search_patterns(strs, [
            "port", "socket", "udp", "tcp", "adb", "reverse", "forward",
            "resolution", "fps", "h264", "hevc", "avc", "nvdec", "d3d", "cuda",
            "audio", "iriun", "format", "pipe", "device", "directshow", "media foundation",
            "virtual", "driver", "width", "height"
        ])
        for kw, hits in kw_results.items():
            if hits:
                print(f"[{kw}]: {hits[:5]}")

print("\n=== Analyzing Iriun Android native lib ===")
native_so = "scratch_iriun/apk/lib/arm64-v8a/libnative-lib.so"
if os.path.exists(native_so):
    strs = extract_strings(native_so)
    print(f"\n--- {native_so} (total strings: {len(strs)}) ---")
    kw_results = search_patterns(strs, [
        "camera", "codec", "encode", "mediacodec", "surface", "socket", "tcp", "udp",
        "h264", "hevc", "nv21", "yuv", "bitrate", "fps", "resolution", "port", "audio", "oboe", "packet"
    ])
    for kw, hits in kw_results.items():
        if hits:
            print(f"[{kw}]: {hits[:5]}")
