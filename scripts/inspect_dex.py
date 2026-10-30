import os
import re
import struct

def parse_dex_strings_and_classes(dex_path):
    with open(dex_path, 'rb') as f:
        data = f.read()

    magic = data[:8]
    if not magic.startswith(b'dex\n'):
        print("Not a valid DEX file")
        return [], []

    string_ids_size, string_ids_off = struct.unpack_from('<II', data, 56)
    type_ids_size, type_ids_off = struct.unpack_from('<II', data, 64)
    proto_ids_size, proto_ids_off = struct.unpack_from('<II', data, 72)
    field_ids_size, field_ids_off = struct.unpack_from('<II', data, 80)
    method_ids_size, method_ids_off = struct.unpack_from('<II', data, 88)
    class_defs_size, class_defs_off = struct.unpack_from('<II', data, 96)

    print(f"DEX Header: {string_ids_size} strings, {type_ids_size} types, {method_ids_size} methods, {class_defs_size} classes")

    # Read string offsets
    string_offsets = []
    for i in range(string_ids_size):
        off = struct.unpack_from('<I', data, string_ids_off + i * 4)[0]
        string_offsets.append(off)

    strings = []
    for off in string_offsets:
        # read uleb128 length
        idx = off
        length = 0
        shift = 0
        while True:
            b = data[idx]
            idx += 1
            length |= (b & 0x7F) << shift
            if (b & 0x80) == 0:
                break
            shift += 7
        try:
            s = data[idx:idx+length].decode('utf-8', errors='ignore')
        except:
            s = ""
        strings.append(s)

    # Read type_ids to get class names
    types = []
    for i in range(type_ids_size):
        descriptor_idx = struct.unpack_from('<I', data, type_ids_off + i * 4)[0]
        types.append(strings[descriptor_idx] if descriptor_idx < len(strings) else "")

    # Read class_defs
    classes = []
    for i in range(class_defs_size):
        class_idx = struct.unpack_from('<I', data, class_defs_off + i * 32)[0]
        classes.append(types[class_idx] if class_idx < len(types) else "")

    return strings, classes

strings, classes = parse_dex_strings_and_classes("scratch_iriun/apk/classes.dex")

iriun_classes = [c for c in classes if "iriun" in c.lower() or "jacksoftw" in c.lower()]
print(f"\n--- Found {len(iriun_classes)} Iriun classes ---")
for c in sorted(iriun_classes):
    print(" ", c)

print("\n--- Relevant Iriun Strings ---")
keywords = ["camera2", "resolution", "mediacodec", "surface", "fps", "bitrate", "port", "usb", "wifi", "connect", "audio", "torch", "zoom", "exposure", "focus", "format"]
for kw in keywords:
    matches = [s for s in strings if kw in s.lower() and len(s) < 100 and any(c.lower() in s.lower() for c in ["iriun", "video", "cam", "socket", "stream", "buffer", "encoder"] or len(s) < 40)]
    # filter duplicates
    matches = list(set(matches))[:10]
    if matches:
        print(f"[{kw}]: {matches[:6]}")
