import unittest

from cc433.bitbuffer import BitBuffer
from tests._helpers import add_bits


# Define the TestBitBuffer class, which groups related state and behavior for this stage.
class TestBitBuffer(unittest.TestCase):
    # Define test___init____starts_empty(), a named step in the decoding/support pipeline.
    def test___init____starts_empty(self):
        bb = BitBuffer()
        self.assertEqual(bb.num_rows, 0)
        self.assertEqual(bb.free_row, 0)

    # Define test_clear__resets_rows_and_bits(), a named step in the decoding/support pipeline.
    def test_clear__resets_rows_and_bits(self):
        bb = add_bits(BitBuffer(), "101")
        bb.clear()
        self.assertEqual(bb.num_rows, 0)
        self.assertEqual(bb.hex_rows(), [])

    # Define test__ensure_first_row__creates_row_zero(), a named step in the decoding/support pipeline.
    def test__ensure_first_row__creates_row_zero(self):
        bb = BitBuffer()
        bb._ensure_first_row()
        self.assertEqual(bb.num_rows, 1)
        self.assertEqual(bb.free_row, 1)

    # Define test_add_bit__packs_msb_first(), a named step in the decoding/support pipeline.
    def test_add_bit__packs_msb_first(self):
        bb = add_bits(BitBuffer(), "10110000")
        self.assertEqual(bb.row_bytes(0), bytes([0xB0]))

    # Define test_add_row__starts_new_row(), a named step in the decoding/support pipeline.
    def test_add_row__starts_new_row(self):
        bb = add_bits(BitBuffer(), "1")
        bb.add_row()
        bb.add_bit(0)
        self.assertEqual(bb.num_rows, 2)
        self.assertEqual(bb.bits_per_row[:2], [1, 1])

    # Define test_add_sync__records_sync_on_empty_row(), a named step in the decoding/support pipeline.
    def test_add_sync__records_sync_on_empty_row(self):
        bb = BitBuffer()
        bb.add_sync()
        self.assertEqual(bb.num_rows, 1)
        self.assertEqual(bb.syncs_before_row[0], 1)

    # Define test_add_sync__moves_after_non_empty_row(), a named step in the decoding/support pipeline.
    def test_add_sync__moves_after_non_empty_row(self):
        bb = add_bits(BitBuffer(), "1")
        bb.add_sync()
        self.assertEqual(bb.num_rows, 2)
        self.assertEqual(bb.syncs_before_row[1], 1)

    # Define test_invert__flips_only_used_bits(), a named step in the decoding/support pipeline.
    def test_invert__flips_only_used_bits(self):
        bb = add_bits(BitBuffer(), "101")
        bb.invert()
        self.assertEqual(bb.extract_bytes(0, 0, 3), bytes([0b01000000]))

    # Define test_clone__returns_independent_copy(), a named step in the decoding/support pipeline.
    def test_clone__returns_independent_copy(self):
        bb = add_bits(BitBuffer(), "1")
        clone = bb.clone()
        clone.add_bit(1)
        self.assertEqual(bb.bits_per_row[0], 1)
        self.assertEqual(clone.bits_per_row[0], 2)

    # Define test_row_bytes__rounds_up_to_full_bytes(), a named step in the decoding/support pipeline.
    def test_row_bytes__rounds_up_to_full_bytes(self):
        bb = add_bits(BitBuffer(), "101")
        self.assertEqual(bb.row_bytes(0), bytes([0xA0]))

    # Define test_extract_bytes__extracts_unaligned_bits(), a named step in the decoding/support pipeline.
    def test_extract_bytes__extracts_unaligned_bits(self):
        bb = add_bits(BitBuffer(), "11010110")
        self.assertEqual(bb.extract_bytes(0, 2, 4), bytes([0b01010000]))

    # Define test_get_bit__returns_single_bit(), a named step in the decoding/support pipeline.
    def test_get_bit__returns_single_bit(self):
        bb = add_bits(BitBuffer(), "10")
        self.assertEqual(bb.get_bit(0, 0), 1)
        self.assertEqual(bb.get_bit(0, 1), 0)

    # Define test_compare_rows__matches_equal_rows(), a named step in the decoding/support pipeline.
    def test_compare_rows__matches_equal_rows(self):
        bb = add_bits(BitBuffer(), "101")
        bb.add_row()
        add_bits(bb, "101")
        self.assertTrue(bb.compare_rows(0, 1))

    # Define test_count_repeats__counts_equal_rows(), a named step in the decoding/support pipeline.
    def test_count_repeats__counts_equal_rows(self):
        bb = add_bits(BitBuffer(), "101")
        bb.add_row(); add_bits(bb, "101")
        self.assertEqual(bb.count_repeats(0), 2)

    # Define test_find_repeated_row__finds_full_repeated_row(), a named step in the decoding/support pipeline.
    def test_find_repeated_row__finds_full_repeated_row(self):
        bb = add_bits(BitBuffer(), "101")
        bb.add_row(); add_bits(bb, "101")
        self.assertEqual(bb.find_repeated_row(2, 3), 0)

    # Define test_find_repeated_prefix__finds_repeated_prefix(), a named step in the decoding/support pipeline.
    def test_find_repeated_prefix__finds_repeated_prefix(self):
        bb = add_bits(BitBuffer(), "1010")
        bb.add_row(); add_bits(bb, "1011")
        self.assertEqual(bb.find_repeated_prefix(2, 3), 0)

    # Define test_hex_rows__returns_uppercase_hex_strings(), a named step in the decoding/support pipeline.
    def test_hex_rows__returns_uppercase_hex_strings(self):
        bb = add_bits(BitBuffer(), "11110000")
        self.assertEqual(bb.hex_rows(), ["F0"])


# Check this condition so only the matching signal/data case is handled here.
if __name__ == "__main__":
    unittest.main()
