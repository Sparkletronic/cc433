# -----------------------------------------------------------------------------
# bitbuffer.py
# BitBuffer stores decoded 0/1 rows in the same spirit as rtl_433 before device-specific decoding.
# Comments in this project are intentionally verbose so a reader who is new to
# radio decoding can follow the signal path from RF edges to decoded records.
# -----------------------------------------------------------------------------

# cc433/bitbuffer.py
# MicroPython subset of rtl_433 bitbuffer.h / bitbuffer.c.

BITBUF_COLS = 128
BITBUF_ROWS = 50
BITBUF_MAX_ROW_BITS = BITBUF_ROWS * BITBUF_COLS * 8


# Define the BitBuffer class, which groups related state and behavior for this stage.
class BitBuffer:
    # Define __init__(), a named step in the decoding/support pipeline.
    def __init__(self):
        self.clear()

    # Define clear(), a named step in the decoding/support pipeline.
    def clear(self):
        self.num_rows = 0
        self.free_row = 0
        self.bits_per_row = [0] * BITBUF_ROWS
        self.syncs_before_row = [0] * BITBUF_ROWS
        self.bb = [bytearray(BITBUF_COLS) for _ in range(BITBUF_ROWS)]

    # Define _ensure_first_row(), a named step in the decoding/support pipeline.
    def _ensure_first_row(self):
        # Check this condition so only the matching signal/data case is handled here.
        if self.num_rows == 0:
            self.free_row = 1
            self.num_rows = 1

    # Define add_bit(), a named step in the decoding/support pipeline.
    def add_bit(self, bit):
        self._ensure_first_row()
        row = self.num_rows - 1
        width = self.bits_per_row[row]
        # Check this condition so only the matching signal/data case is handled here.
        if width >= 0xFFFF:
            # Return the result to the caller so the next pipeline stage can continue.
            return

        # rtl_433 can spill a very long logical row into backing rows. For our
        # Acurite path this should not happen, but keep the same guard shape.
        col_index = width // 8
        bit_index = width & 7
        # Check this condition so only the matching signal/data case is handled here.
        if col_index >= BITBUF_COLS:
            # Return the result to the caller so the next pipeline stage can continue.
            return
        # Check this condition so only the matching signal/data case is handled here.
        if bit:
            self.bb[row][col_index] |= 1 << (7 - bit_index)
        self.bits_per_row[row] = width + 1

    # Define add_row(), a named step in the decoding/support pipeline.
    def add_row(self):
        self._ensure_first_row()
        # Check this condition so only the matching signal/data case is handled here.
        if self.free_row < BITBUF_ROWS:
            self.free_row += 1
            self.num_rows = self.free_row
        # Handle the fallback case when none of the earlier conditions matched.
        else:
            # rtl_433 clears the last row to handle overflow somewhat gracefully.
            self.bits_per_row[self.num_rows - 1] = 0
            self.bb[self.num_rows - 1] = bytearray(BITBUF_COLS)

    # Define add_sync(), a named step in the decoding/support pipeline.
    def add_sync(self):
        self._ensure_first_row()
        # Check this condition so only the matching signal/data case is handled here.
        if self.bits_per_row[self.num_rows - 1]:
            self.add_row()
        self.syncs_before_row[self.num_rows - 1] += 1

    # Define invert(), a named step in the decoding/support pipeline.
    def invert(self):
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for row in range(self.num_rows):
            bit_len = self.bits_per_row[row]
            # Check this condition so only the matching signal/data case is handled here.
            if bit_len <= 0:
                # Skip the rest of this iteration and move on to the next candidate.
                continue
            last_col = (bit_len - 1) // 8
            last_bits = ((bit_len - 1) & 7) + 1
            # Iterate through each item so the pipeline can process one measured/test value at a time.
            for col in range(last_col + 1):
                self.bb[row][col] ^= 0xFF
            self.bb[row][last_col] ^= 0xFF >> last_bits


    # Define clone(), a named step in the decoding/support pipeline.
    def clone(self):
        other = BitBuffer()
        other.num_rows = self.num_rows
        other.free_row = self.free_row
        other.bits_per_row = self.bits_per_row[:]
        other.syncs_before_row = self.syncs_before_row[:]
        other.bb = [bytearray(row) for row in self.bb]
        # Return the result to the caller so the next pipeline stage can continue.
        return other

    # Define row_bytes(), a named step in the decoding/support pipeline.
    def row_bytes(self, row):
        n = (self.bits_per_row[row] + 7) // 8
        # Return the result to the caller so the next pipeline stage can continue.
        return bytes(self.bb[row][:n])

    # Define extract_bytes(), a named step in the decoding/support pipeline.
    def extract_bytes(self, row, pos, length_bits):
        # Check this condition so only the matching signal/data case is handled here.
        if length_bits == 0:
            # Return the result to the caller so the next pipeline stage can continue.
            return b""
        out = bytearray((length_bits + 7) // 8)
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for i in range(length_bits):
            # Check this condition so only the matching signal/data case is handled here.
            if self.get_bit(row, pos + i):
                out[i >> 3] |= 1 << (7 - (i & 7))
        # Check this condition so only the matching signal/data case is handled here.
        if length_bits & 7:
            out[(length_bits - 1) // 8] &= 0xFF << (8 - (length_bits & 7))
        # Return the result to the caller so the next pipeline stage can continue.
        return bytes(out)

    # Define get_bit(), a named step in the decoding/support pipeline.
    def get_bit(self, row, bit_idx):
        # Return the result to the caller so the next pipeline stage can continue.
        return (self.bb[row][bit_idx >> 3] >> (7 - (bit_idx & 7))) & 1

    # Define compare_rows(), a named step in the decoding/support pipeline.
    def compare_rows(self, row_a, row_b, max_bits=0):
        len_a = self.bits_per_row[row_a]
        len_b = self.bits_per_row[row_b]
        # Check this condition so only the matching signal/data case is handled here.
        if max_bits == 0 or len_a < max_bits or len_b < max_bits:
            # Check this condition so only the matching signal/data case is handled here.
            if len_a != len_b:
                # Return the result to the caller so the next pipeline stage can continue.
                return False
            max_bits = len_a
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for bit in range(max_bits):
            # Check this condition so only the matching signal/data case is handled here.
            if self.get_bit(row_a, bit) != self.get_bit(row_b, bit):
                # Return the result to the caller so the next pipeline stage can continue.
                return False
        # Return the result to the caller so the next pipeline stage can continue.
        return True

    # Define count_repeats(), a named step in the decoding/support pipeline.
    def count_repeats(self, row, max_bits=0):
        cnt = 0
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for i in range(self.num_rows):
            # Check this condition so only the matching signal/data case is handled here.
            if self.compare_rows(row, i, max_bits):
                cnt += 1
        # Return the result to the caller so the next pipeline stage can continue.
        return cnt

    # Define find_repeated_row(), a named step in the decoding/support pipeline.
    def find_repeated_row(self, min_repeats, min_bits):
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for i in range(self.num_rows):
            # Check this condition so only the matching signal/data case is handled here.
            if self.bits_per_row[i] >= min_bits and self.count_repeats(i, 0) >= min_repeats:
                # Return the result to the caller so the next pipeline stage can continue.
                return i
        # Return the result to the caller so the next pipeline stage can continue.
        return -1

    # Define find_repeated_prefix(), a named step in the decoding/support pipeline.
    def find_repeated_prefix(self, min_repeats, min_bits):
        # Iterate through each item so the pipeline can process one measured/test value at a time.
        for i in range(self.num_rows):
            # Check this condition so only the matching signal/data case is handled here.
            if self.bits_per_row[i] >= min_bits and self.count_repeats(i, min_bits) >= min_repeats:
                # Return the result to the caller so the next pipeline stage can continue.
                return i
        # Return the result to the caller so the next pipeline stage can continue.
        return -1

    # Define hex_rows(), a named step in the decoding/support pipeline.
    def hex_rows(self):
        # Return the result to the caller so the next pipeline stage can continue.
        return [self.row_bytes(i).hex().upper() for i in range(self.num_rows)]
