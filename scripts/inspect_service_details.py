import struct

with open("scratch_iriun/apk/classes.dex", "rb") as f:
    dex = f.read()

string_ids_size, string_ids_off = struct.unpack_from('<II', dex, 56)
type_ids_size, type_ids_off = struct.unpack_from('<II', dex, 64)
proto_ids_size, proto_ids_off = struct.unpack_from('<II', dex, 72)
field_ids_size, field_ids_off = struct.unpack_from('<II', dex, 80)
method_ids_size, method_ids_off = struct.unpack_from('<II', dex, 88)
class_defs_size, class_defs_off = struct.unpack_from('<II', dex, 96)

strings = []
for i in range(string_ids_size):
    off = struct.unpack_from('<I', dex, string_ids_off + i * 4)[0]
    idx = off
    length = 0
    shift = 0
    while True:
        b = dex[idx]
        idx += 1
        length |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    s = dex[idx:idx+length].decode('utf-8', errors='ignore')
    strings.append(s)

types = [strings[struct.unpack_from('<I', dex, type_ids_off + i * 4)[0]] for i in range(type_ids_size)]

protos = []
for i in range(proto_ids_size):
    shorty_idx, return_type_idx, params_off = struct.unpack_from('<III', dex, proto_ids_off + i * 12)
    protos.append((strings[shorty_idx], types[return_type_idx]))

fields = []
for i in range(field_ids_size):
    class_idx, type_idx, name_idx = struct.unpack_from('<HHI', dex, field_ids_off + i * 8)
    fields.append((types[class_idx], types[type_idx], strings[name_idx]))

methods = []
for i in range(method_ids_size):
    class_idx, proto_idx, name_idx = struct.unpack_from('<HHI', dex, method_ids_off + i * 8)
    methods.append((types[class_idx], protos[proto_idx], strings[name_idx]))

print("=== Fields in LocalService ===")
for cls, type_name, field_name in fields:
    if "LocalService" in cls:
        print(f"  {field_name}: {type_name}")

print("\n=== Methods in LocalService with return types ===")
for cls, (shorty, ret_type), meth_name in methods:
    if "LocalService" in cls:
        print(f"  {meth_name} -> {ret_type} (shorty: {shorty})")
