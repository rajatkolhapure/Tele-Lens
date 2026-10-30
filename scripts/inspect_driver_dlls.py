import re
import glob

def check_dll(path):
    with open(path, 'rb') as f:
        data = f.read()
    strs = re.findall(rb'[ -~]{4,}', data)
    decoded = [s.decode('latin-1') for s in strs]
    print(f"\n=== Strings in {path} ({len(decoded)}) ===")
    for s in decoded:
        if any(k in s.lower() for k in ["shm", "share", "pipe", "map", "event", "mutex", "iriun", "section", "buffer", "nv12", "yuy2", "rgb"]):
            print("  ", s)

for f in glob.glob('scratch_iriun/win/**/iriunv*.dll', recursive=True):
    check_dll(f)
