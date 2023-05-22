import time
import argparse

from random import seed
from datetime import timedelta

from fuzzer import Fuzzer
from minimizer import Minimizer

from os.path import join, dirname, basename

from utils.helper import FileManager, VersionManager, IOQueue

class Metamong:
    def __init__(self, input_dir: str, output_dir: str, num_of_threads: int,
                 browser_type:str, base_version: int, target_version: int) -> None:

        self.in_dir = input_dir
        self.out_dir = output_dir
        self.num_of_threads = num_of_threads
        self.browser_type = browser_type
        self.base_ver = base_version
        self.target_ver = target_version

        self.experiment_result = {}
        self.tester = [
            Fuzzer,
            Minimizer,
        ]
        self.report = [
            Fuzzer,
        ]


    def skip_minimizer(self):
        self.tester.remove(Minimizer)

    def test_wrapper(self, test_class: object, report: bool = False) -> None:
        start = time.time()
        threads = []
        for i in range(self.num_of_threads):
            threads.append(test_class(self.ioq, self.browser_type))
            threads[-1].saveshot = report

        class_name = type(threads[-1]).__name__
        print (f'{class_name} stage starts...')

        for th in threads:
            th.start()

        num_th = len(threads)
        alive = num_th
        while True:
            self.ioq.monitoring()
            time.sleep(1)

            alive = 0
            for th in threads:
                if th.is_alive(): alive += 1

            if alive == 0: break

            if alive < num_th:
                left = self.ioq.left()
                print (f'{alive} of {num_th} Threads are alive, {left} inputs are left...')

        self.ioq.reset_lock()
        elapsed = time.time() - start
        elapsed_time = str(timedelta(seconds=elapsed))
        print (f'{class_name} stage ends...', elapsed_time)

        if not report:
            self.experiment_result[class_name] = [self.ioq.num_of_outputs, elapsed_time]
        self.ioq.move_to_preqs()
        if not report:
            dirname = class_name
            dir_path = join(self.out_dir, dirname)
            self.ioq.dump_queue(dir_path)


    def process(self) -> None:
        start = time.time()

        self.vm = VersionManager(self.browser_type)
        testcases = FileManager.get_all_files(self.in_dir, '.html', 'expected.html')
        rev_range = self.vm.get_rev_range(self.base_ver, self.target_ver)


        num_of_tests = len(testcases)
        rev_a = rev_range[0]
        rev_b = rev_range[-1]

        print (f'# of tests: {num_of_tests}, rev_a: {rev_a}, rev_b: {rev_b}')

        self.ioq = IOQueue(testcases, rev_range)

        for test in self.tester: 
            self.test_wrapper(test)

        elapsed = time.time() - start
        self.experiment_result['TOTAL TIME'] = str(timedelta(seconds=elapsed))

        if self.report:
            self.ioq.dump_queue_with_sort(join(self.out_dir, 'Report'))
            for test in self.report: 
                self.test_wrapper(test, True)

        print (self.experiment_result)

def main():
    parser = argparse.ArgumentParser(description='Usage')
    parser.add_argument('-i', '--input', required=True, type=str, default='', help='input directory')
    parser.add_argument('-o', '--output', required=True, type=str, help='output directory')
    parser.add_argument('-j', '--job', required=False, type=int, default=1, help='number of threads')
    parser.add_argument('-t', '--type', required=False, type=str, default='chrome', help='Browser type')
    parser.add_argument('-p', '--pre', required=True, type=int, help='Version of base Chrome (e.g., 80)')
    parser.add_argument('-n', '--new', required=True, type=int, help='version of target Chrome (e.g., 81)')
    parser.add_argument('--nomin', action='store_true',    help='No minimization')
    args = parser.parse_args()

    seed(0)

    m = Metamong(args.input, args.output, args.job, args.type, args.pre, args.new)
    if args.nomin:
        m.skip_minimizer()
    m.process()


if __name__ == "__main__":
    main()
