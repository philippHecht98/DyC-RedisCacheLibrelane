#!/usr/bin/env python3
"""
Convert a flat binary firmware image to a Verilog $readmemh-compatible .hex
file (one 32-bit word per line, little-endian byte order).

Usage:
    python3 bin2hex.py firmware.bin firmware.hex [num_words]

num_words (optional) pads/truncates to exactly that many words (default: 16384 = 64KB/4).
"""

import sys, struct

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.bin> <output.hex> [num_words]")
        sys.exit(1)

    in_path  = sys.argv[1]
    out_path = sys.argv[2]
    num_words = int(sys.argv[3]) if len(sys.argv) > 3 else 16384  # 64 KB

    with open(in_path, "rb") as f:
        data = f.read()

    # Pad to word boundary
    while len(data) % 4:
        data += b'\x00'

    words = struct.unpack(f"<{len(data)//4}I", data)

    with open(out_path, "w") as f:
        for i in range(num_words):
            w = words[i] if i < len(words) else 0
            f.write(f"{w:08x}\n")

    print(f"Wrote {num_words} words to {out_path}")

if __name__ == "__main__":
    main()
