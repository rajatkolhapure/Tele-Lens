import re

def find_resolutions(path):
    with open(path, 'rb') as f:
        data = f.read()

    # Look for resolution patterns like WxH
    matches = re.findall(rb'\b\d{3,4}x\d{3,4}\b', data)
    print(f"\n=== Resolution strings in {path} ===")
    print(set([m.decode('latin-1') for m in matches]))

find_resolutions("scratch_iriun/win/IriunWebcam.exe")
find_resolutions("scratch_iriun/win/engine.dll")
find_resolutions("scratch_iriun/apk/lib/arm64-v8a/libnative-lib.so")
