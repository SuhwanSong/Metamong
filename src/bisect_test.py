import unittest

from modules import CrossVersion
from modules import Bisecter

from helper import IOQueue
from collections import deque 


class BisectTester(Bisecter):
    def __init__(self, helper: IOQueue, browser_type: str) -> None:
        super().__init__(helper, browser_type)

        self.build = True
        self.func = None

    def start_ref_browser(self, ver: int) -> bool:
        return True

    def stop_ref_browser(self) -> None:
        pass

    def get_chrome(self, ver: int) -> None:
        pass

    def metamor_test(self, html_file: str, muts: list):
        return self.func(self.cur_mid)

def assert_():
      raise RuntimeError('assert')

class fake:
    not_bug = False
    bug = True
    crash = None

# Bisects from start to end using the results in the bisect_results map. Each
# value in bisect_results should be checked exactly once, to ensure that we do
# not do too many or too few tests.
def test_bisect_(start, end, bisect_results) -> int:
    def getResultByRevision(rev):
        if rev in bisect_results:
            retval = bisect_results[rev]
            # Delete the result because each result should only be tested once.
            del bisect_results[rev]
            return retval
        raise RuntimeError('Bisected to an unexpected revision')

    empty = {}
    ioq = IOQueue(empty, [start, end])
    ioq.insert_to_queue((start, end), 'test', [''])

    bi = BisectTester(ioq, 'chrome')
    bi.func = getResultByRevision
    bi.start()
    bi.join()
    ioq.move_to_preqs()
    vers = ioq.get_vers()
    if len(bisect_results) != 0:
        raise RuntimeError('Did not check all of the expected bisect results')
    if not vers:
        return None
    return vers[1]

class TestBisecter(unittest.TestCase):
    def test_noop(self):
        bisect_results = {
          5: fake.not_bug,
          6: fake.bug,
        }
        self.assertEqual(6, test_bisect_(5, 6, bisect_results))

    def test3_1(self):
        bisect_results = {
          5: fake.not_bug,
          6: fake.not_bug,
          7: fake.bug,
        }
        self.assertEqual(7, test_bisect_(5, 7, bisect_results))

    def test3_2(self):
        bisect_results = {
          5: fake.not_bug,
          6: fake.bug,
          7: fake.bug,
        }
        self.assertEqual(6, test_bisect_(5, 7, bisect_results))

    def test4_1(self):
        bisect_results = {
          5: fake.not_bug,
          6: fake.bug,
          7: fake.bug,
          9: fake.bug,
        }
        self.assertEqual(6, test_bisect_(5, 9, bisect_results))

    def test4_2(self):
        bisect_results = {
          5: fake.not_bug,
          6: fake.not_bug,
          7: fake.bug,
          9: fake.bug,
        }
        self.assertEqual(7, test_bisect_(5, 9, bisect_results))

    def test4_3(self):
        bisect_results = {
          5: fake.not_bug,
          7: fake.not_bug,
          8: fake.bug,
          9: fake.bug,
        }
        self.assertEqual(8, test_bisect_(5, 9, bisect_results))

    def test4_4(self):
        bisect_results = {
          5: fake.not_bug,
          7: fake.not_bug,
          8: fake.not_bug,
          9: fake.bug,
        }
        self.assertEqual(9, test_bisect_(5, 9, bisect_results))

    # If we encounter a crash, bail. This could be improved by ignoring
    # this revision and continuing the bisect, but this issue is fairly
    # rare.
    def test_mid_crash(self):
        bisect_results = {
          5: fake.not_bug,
          7: fake.crash,
          9: fake.bug,
        }
        self.assertEqual(None, test_bisect_(5, 9, bisect_results))

    # See comment above |test_mid_crash|.
    def test_left_crash(self):
        bisect_results = {
          5: fake.not_bug,
          6: fake.crash,
          7: fake.bug,
          9: fake.bug,
        }
        self.assertEqual(None, test_bisect_(5, 9, bisect_results))

    # See comment above |test_mid_crash|.
    def test_right_crash(self):
        bisect_results = {
          5: fake.not_bug,
          7: fake.not_bug,
          8: fake.crash,
          9: fake.bug,
        }
        self.assertEqual(None, test_bisect_(5, 9, bisect_results))
