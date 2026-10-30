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

# Find LocalService class_def
for i in range(class_defs_size):
    class_idx, access_flags, superclass_idx, interfaces_off, source_file_idx, annotations_off, class_data_off, static_values_off = struct.unpack_from('<IIIIIIII', dex, class_defs_off + i * 32)
    cname = types[class_idx]
    if "LocalService" in cname and not "$" in cname:
        print(f"Found class: {cname} at data off {class_data_off}")
        off = class_data_off
        static_fields_size, off = read_uleb128(dex, off)
        instance_fields_size, off = read_uleb128(dex, off)
        direct_methods_size, off = read_uleb128(dex, off)
        virtual_methods_size, off = read_uleb128(dex, off)

        print(f"Static fields: {static_fields_size}, Instance: {instance_fields_size}, Direct methods: {direct_methods_size}, Virtual: {virtual_methods_size}")

        field_idx = 0
        for _ in range(static_fields_size):
            f_diff, off = read_uleb128(dex, off)
            flags, off = read_uleb128(dex, off)
        for _ in range(instance_fields_size):
            f_diff, off = read_uleb128(dex, off)
            flags, off = read_uleb128(dex, off)

        method_idx = 0
        for m_i in range(direct_methods_size + virtual_methods_size):
            m_diff, off = read_uleb128(dex, off)
            access_flags, off = read_uleb128(dex, off)
            code_off, off = read_uleb128(dex, off)
            method_idx += m_diff
            cls_name, m_name = methods[method_idx]

            # Let's inspect code_off if present
            if code_off != 0:
                registers_size, ins_size, outs_size, tries_size, debug_info_off, insns_size = struct.unpack_from('<HHHHII', dex, code_off)
                insns = dex[code_off + 16 : code_off + 16 + insns_size * 2]
                
                # Check for const-string or invoke-virtual/static
                method_strings = []
                method_invokes = []
                # Scan instructions
                idx = 0
                while idx < len(insns):
                    op = insns[idx]
                    if op in (0x1a,): # const-string
                        str_idx = struct.unpack_from('<H', insns, idx + 2)[0]
                        if str_idx < len(strings):
                            method_strings.append(strings[str_idx])
                        idx += 4
                    elif op in (0x1b,): # const-string/jumbo
                        str_idx = struct.unpack_from('<I', insns, idx + 2)[0]
                        if str_idx < len(strings):
                            method_strings.append(strings[str_idx])
                        idx += 6
                    elif op in (0x6e, 0x6f, 0x70, 0x71, 0x72): # invoke-kind
                        target_idx = struct.unpack_from('<H', insns, idx + 2)[0]
                        if target_idx < len(methods):
                            method_invokes.append(f"{methods[target_idx][0]}->{methods[target_idx][1]}")
                        idx += 6
                    elif op in (0x74, 0x75, 0x76, 0x77, 0x78): # invoke-kind/range
                        target_idx = struct.unpack_from('<H', insns, idx + 2)[0]
                        if target_idx < len(methods):
                            method_invokes.append(f"{methods[target_idx][0]}->{methods[target_idx][1]}")
                        idx += 6
                    else:
                        idx += 2

                if any(k in m_name.lower() for k in ["start", "camera", "codec", "size", "init", "create", "setup", "run", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p"]):
                    interesting_calls = [inv for inv in method_invokes if any(k in inv for k in ["Camera", "MediaCodec", "Surface", "Nsd", "create", "configure", "start", "set", "native", "Size"])]
                    if interesting_calls or method_strings:
                        print(f"\n--- Method: {m_name} (regs: {registers_size}, insns: {insns_size}) ---")
                        if method_strings:
                            print("  Strings:", method_strings[:10])
                        if interesting_calls:
                            print("  Calls:", interesting_calls[:15])
