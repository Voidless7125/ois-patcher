import unittest
import sys
import os

# Add the parent directory to sys.path so we can import personal_variants
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import personal_variants

class TestPersonalVariants(unittest.TestCase):
    def test_data_fixes_format(self):
        """Ensure DATA_FIXES is a dictionary with list of tuples as values."""
        self.assertTrue(hasattr(personal_variants, 'DATA_FIXES'), "DATA_FIXES must be defined")
        
        fixes = personal_variants.DATA_FIXES
        self.assertIsInstance(fixes, dict, "DATA_FIXES must be a dictionary")
        
        for filename, replacements in fixes.items():
            self.assertIsInstance(filename, str, "Keys in DATA_FIXES must be strings (filenames)")
            self.assertIsInstance(replacements, list, "Values in DATA_FIXES must be lists of replacements")
            
            for rep in replacements:
                self.assertIsInstance(rep, tuple, "Each replacement must be a tuple")
                self.assertIn(len(rep), [3, 4], "Replacements must be tuples of length 3 or 4: (count, search, replace, [optional_flags])")
                self.assertIsInstance(rep[0], int, "First element of replacement tuple must be an integer (count)")
                self.assertIsInstance(rep[1], str, "Second element of replacement tuple must be a string (search)")
                self.assertIsInstance(rep[2], str, "Third element of replacement tuple must be a string (replace)")

    def test_apply_exe_fixes_signature(self):
        """Ensure apply_exe_fixes accepts the expected arguments."""
        self.assertTrue(hasattr(personal_variants, 'apply_exe_fixes'), "apply_exe_fixes must be defined")
        
        import inspect
        sig = inspect.signature(personal_variants.apply_exe_fixes)
        params = list(sig.parameters.keys())
        expected_params = ['data', 'pe', 'ptch_va', 'ptch_off', 'cave_cursor']
        
        # Check that the first 5 parameters match what the patcher expects
        for expected in expected_params:
            self.assertIn(expected, params, f"apply_exe_fixes missing expected parameter: {expected}")

if __name__ == '__main__':
    unittest.main()
