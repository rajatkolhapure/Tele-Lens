import struct

def parse_pe_exports(pe_path):
    with open(pe_path, 'rb') as f:
        data = f.read()

    # DOS header
    e_lfanew = struct.unpack_from('<I', data, 0x3C)[0]
    pe_sig = data[e_lfanew:e_lfanew+4]
    if pe_sig != b'PE\x00\x00':
        print("Not PE")
        return []

    # Optional header
    magic = struct.unpack_from('<H', data, e_lfanew + 24)[0]
    is_64 = (magic == 0x20B)
    data_dir_off = e_lfanew + 24 + (112 if is_64 else 96)

    export_rva, export_size = struct.unpack_from('<II', data, data_dir_off)
    if export_rva == 0:
        print("No export directory")
        return []

    # Number of sections
    num_sections = struct.unpack_from('<H', data, e_lfanew + 6)[0]
    opt_header_size = struct.unpack_from('<H', data, e_lfanew + 20)[0]
    section_headers_off = e_lfanew + 24 + opt_header_size

    def rva_to_offset(rva):
        for i in range(num_sections):
            sec_off = section_headers_off + i * 40
            sec_vsize, sec_va, sec_rsize, sec_raw = struct.unpack_from('<IIII', data, sec_off + 8)
            if sec_va <= rva < sec_va + sec_vsize:
                return sec_raw + (rva - sec_va)
        return None

    exp_off = rva_to_offset(export_rva)
    if not exp_off:
        print("Could not map export directory")
        return []

    num_funcs, num_names, names_rva = struct.unpack_from('<III', data, exp_off + 20 + 4)
    # Actually export dir structure:
    # 0: Characteristics
    # 4: TimeDateStamp
    # 8: Major/Minor
    # 12: Name RVA
    # 16: Base
    # 20: NumberOfFunctions
    # 24: NumberOfNames
    # 28: AddressOfFunctions
    # 32: AddressOfNames
    # 36: AddressOfNameOrdinals
    num_funcs, num_names, funcs_rva, names_rva, ords_rva = struct.unpack_from('<IIIII', data, exp_off + 20)
    print(f"PE Exports: {num_names} named exports out of {num_funcs} functions")

    names = []
    names_off = rva_to_offset(names_rva)
    for i in range(num_names):
        name_rva = struct.unpack_from('<I', data, names_off + i * 4)[0]
        n_off = rva_to_offset(name_rva)
        if n_off:
            end = data.find(b'\x00', n_off)
            names.append(data[n_off:end].decode('latin-1'))
    return names

exports = parse_pe_exports("scratch_iriun/win/engine.dll")
for exp in exports:
    print("  Export:", exp)
