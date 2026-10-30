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
methods = []
for i in range(method_ids_size):
    class_idx, proto_idx, name_idx = struct.unpack_from('<HHI', dex, method_ids_off + i * 8)
    methods.append((types[class_idx], strings[name_idx]))

fields = []
for i in range(field_ids_size):
    class_idx, type_idx, name_idx = struct.unpack_from('<HHI', dex, field_ids_off + i * 8)
    fields.append((types[class_idx], strings[name_idx]))

def read_uleb128(data, off):
    res = 0
    shift = 0
    while True:
        b = data[off]
        off += 1
        res |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            break
        shift += 7
    return res, off

# Scan all string constants and field names used in LocalService
for i in range(class_defs_size):
    class_idx, access_flags, superclass_idx, interfaces_off, source_file_idx, annotations_off, class_data_off, static_values_off = struct.unpack_from('<IIIIIIII', dex, class_defs_off + i * 32)
    cname = types[class_idx]
    if cname == "Lcom/iriun/webcam/LocalService;":
        off = class_data_off
        static_fields_size, off = read_uleb128(dex, off)
        instance_fields_size, off = read_uleb128(dex, off)
        direct_methods_size, off = read_uleb128(dex, off)
        virtual_methods_size, off = read_uleb128(dex, off)

        # skip fields
        for _ in range(static_fields_size + instance_fields_size):
            f_diff, off = read_uleb128(dex, off)
            flags, off = read_uleb128(dex, off)

        method_idx = 0
        for m_i in range(direct_methods_size + virtual_methods_size):
            m_diff, off = read_uleb128(dex, off)
            access_flags, off = read_uleb128(dex, off)
            code_off, off = read_uleb128(dex, off)
            method_idx += m_diff
            cls_name, m_name = methods[method_idx]
            if code_off != 0:
                registers_size, ins_size, outs_size, tries_size, debug_info_off, insns_size = struct.unpack_from('<HHHHII', dex, code_off)
                insns = dex[code_off + 16 : code_off + 16 + insns_size * 2]
                
                # Scan for sget/sput or iget/iput of CameraCharacteristics keys or CaptureRequest keys
                keys_accessed = []
                idx = 0
                while idx < len(insns):
                    op = insns[idx]
                    if op in (0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66): # sget
                        f_idx = struct.unpack_from('<H', insns, idx + 2)[0]
                        if f_idx < len(fields):
                            f_cls, f_n = fields[f_idx]
                            if "CameraCharacteristics" in f_cls or "CaptureRequest" in f_cls:
                                keys_accessed.append(f"{f_cls.split('/')[-1]}::{f_n}")
                    idx += 2
                if keys_accessed:
                    print(f"Method {m_name} accesses Camera/Capture Keys: {sorted(set(keys_accessed))}")
