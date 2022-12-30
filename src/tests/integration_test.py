import os
import filecmp
import unittest

import tempfile
from random import seed

from helper import FileManager
from modules import Metamong

class TestIntegration(unittest.TestCase):
    def test_no_animations(self):
        seed(0)

        root = "testcases"
        base = "integration_test"
        name = "inputs"
        expect = "expect"
        btype = "chrome"

        job = 4
        pre = 85
        new = 106

        in_dir = os.path.join(root, base, name)
        ex_dir = os.path.join(root, base, expect)
        ex_files = FileManager.get_all_files(ex_dir)
        ex_files.sort()
        with tempfile.TemporaryDirectory() as out_dir:
            m = Metamong(in_dir, out_dir, job, btype, pre, new)
            m.skip_minimizer()
            m.process()

            out_files = FileManager.get_all_files(out_dir)
            out_files.sort()

            for a, b in zip(ex_files, out_files):
                self.assertEqual(os.path.basename(a), 
                                 os.path.basename(b))
                self.assertTrue(filecmp.cmp(a,b))
