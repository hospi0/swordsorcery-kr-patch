# -*- coding: utf-8 -*-
"""SSSS.BIN(램 0x06018000) SH-2 디스어셈(마리카 tools/shdis.py 옮김) — 리터럴 값 주석. python tools/shdis.py 시작 끝"""
import struct, sys
import capstone
B = 0x06018000
s = open(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', 'work', 'disc0', 'SSSS.BIN'), 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2 | capstone.CS_MODE_BIG_ENDIAN)


def dis(a, b):
    out = []
    while a < b:
        n0 = len(out)
        for ins in md.disasm(s[a - B:b - B], a):
            a = ins.address + ins.size
            out.append(fmt(ins))
        if len(out) == n0 or a < b:
            if a < b and (len(out) == n0 or True):
                out.append('%08X .word %04X' % (a, struct.unpack_from('>H', s, a - B)[0])); a += 2
    return out


def fmt(ins):
    if True:
        t = ins.op_str; note = ''
        if ins.mnemonic in ('mov.l', 'mov.w') and t.startswith('0x'):
            la = int(t.split(',')[0], 16)
            if B <= la < B + len(s):
                v = struct.unpack_from('>I' if ins.mnemonic == 'mov.l' else '>h', s, la - B)[0]
                note = '    ; =%X' % (v & 0xFFFFFFFF)
        return '%08X %s %s%s' % (ins.address, ins.mnemonic, t, note)


if __name__ == '__main__':
    print('\n'.join(dis(int(sys.argv[1], 16), int(sys.argv[2], 16))))
