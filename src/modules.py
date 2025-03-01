import os
import re
import time

from datetime import timedelta
from pyvirtualdisplay import Display
from os.path import basename, join, dirname

from driver import Browser
from typing import Optional, Tuple

from helper import IOQueue
from helper import ImageDiff
from helper import FileManager
from helper import VersionManager

from threading import Thread
from threading import current_thread

from bisect import bisect

from pathlib import Path
from shutil import copyfile
from bs4 import BeautifulSoup
from collections import defaultdict

from mutater import MetaMut
from multiprocessing import Process

class SingleVersion(Thread):
    def __init__(self, helper: IOQueue, browser_type: str) -> None:
        super().__init__()
        self.br_list = []

        self.helper = helper
        self.__btype = browser_type

        self.report_mode = False
        self.saveshot = False
        self.iter_num = 4


    def report_mode(self) -> None:
        self.report_mode = True
        self.saveshot = True
        self.iter_num = 1

    def get_newer_browser(self) -> Browser:
        return self.br_list[-1] if self.br_list else None

    def start_browsers(self, vers: Tuple[int, int]) -> bool:
        self.stop_browsers()

        bt = self.__btype
        if bt == 'chrome':
            for ver in vers:
                self.helper.download_chrome(ver)
        elif bt == 'firefox':
            for ver in vers:
                self.helper.build_firefox(ver)
        else:
            raise ValueError('Unsupported browser type')

        for ver in vers:
            self.br_list.append(Browser(bt, ver))

        for br in self.br_list:
            if not br.setup_browser():
                return False
        return True

    def stop_browsers(self) -> None:
        for br in self.br_list:
            br.kill_browser()
        self.br_list.clear()

    def test_wrapper(self, br, html_file: str, muts: list, phash: bool = False):
        thread_id = current_thread()
        self.helper.record_current_test(thread_id, br, html_file)
        is_bug = br.metamor_test(html_file, muts, save_shot=self.saveshot, phash=phash)
        self.helper.delete_record(thread_id, br, html_file)
        return is_bug

    def gen_muts(self, html_file: str, muts: list):
        br = self.get_newer_browser()
        meta_mut = MetaMut()
        dic = br.analyze_html(html_file)
        if not dic: return
        meta_mut.load_state(dic)
        muts.extend(meta_mut.generate())

    def single_test_html(self, html_file: str, muts: list, phash: bool = False):
        br = self.get_newer_browser()
        for _ in range(self.iter_num):
            is_bug = self.test_wrapper(br, html_file, muts, phash=phash)
            if not is_bug: return False
        return True

    def run(self) -> None:
        start = time.time()
        cur_vers = None
        hpr = self.helper

        while True:

            popped = hpr.pop_from_queue()
            if not popped: break

            result, vers = popped
            html_file, muts = result

            if cur_vers != vers:
                cur_vers = vers
                ver = cur_vers[-1]
                if not self.start_browsers([ver]):
                    continue

            # This is for eliminating non-invalidation bug.
            br = self.get_newer_browser()
            if self.test_wrapper(br, html_file, [], phash=True):
                os.remove(html_file) 
                continue

            if not muts:
                self.gen_muts(html_file, muts)
                FileManager.write_file(html_file.replace('.html', '.js'), '\n'.join(muts))
                 

            if self.single_test_html(html_file, muts, phash=True):
                hpr.update_postq(vers, html_file, muts)

        self.stop_browsers()

class CrossVersion(SingleVersion):
    def __init__(self, helper: IOQueue, browser_type: str) -> None:
        super().__init__(helper, browser_type)

    def cross_version_test_html(self, html_file: str, muts: list) -> bool:
        thread_id = current_thread()
        br1, br2 = self.br_list

        for _ in range(self.iter_num):
            br1_bug = self.test_wrapper(br1, html_file, muts, phash=True)
            if br1_bug is None: return
            elif br1_bug: return False

            br2_bug = self.test_wrapper(br2, html_file, muts, phash=True)
            if br2_bug is None: return

        return not br1_bug and br2_bug

    def run(self) -> None:
        start = time.time()
        cur_vers = None
        hpr = self.helper

        while True:

            popped = hpr.pop_from_queue()
            if not popped: break

            result, vers = popped
            html_file, muts = result

            if cur_vers != vers:
                cur_vers = vers
                if not self.start_browsers(cur_vers):
                    continue

            if not self.cross_version_test_html(html_file, muts):
                continue

            hpr.update_postq(vers, html_file, muts)

        self.stop_browsers()


class Bisecter(Thread):
    def __init__(self, helper: IOQueue, browser_type: str) -> None:
        super().__init__()
        self.helper = helper
        self.__btype = browser_type

        self.ref_br = None
        self.saveshot = False
        self.cur_mid = None

        self.build = False

    def cross_version_test(self, vers: Tuple[int, int], html_file: str, muts: list):
        cv = CrossVersion(self.helper, self.__btype)
        cv.start_browsers(vers)
        is_bug = cv.cross_version_test_html(html_file, muts)
        cv.stop_browsers()
        del cv
        return is_bug


    def start_ref_browser(self, ver: int) -> bool:
        self.stop_ref_browser()

        bt = self.__btype
        if bt == 'chrome':
            self.helper.download_chrome(ver)
        elif bt == 'firefox':
            self.helper.build_firefox(ver)
        else:
            raise ValueError('Unsupported browser type')

        self.ref_br = Browser(bt, ver)
        return self.ref_br.setup_browser()

    def stop_ref_browser(self) -> None:
        if self.ref_br:
            self.ref_br.kill_browser()
            self.ref_br = None

    def get_browser(self, ver: int) -> None:
        pass

    def metamor_test(self, html_file: str, muts: list):
        thread_id = current_thread()
        br = self.ref_br
        for _ in range(4):
            self.helper.record_current_test(thread_id, br, html_file)
            is_bug = self.ref_br.metamor_test(html_file, muts, self.saveshot)
            self.helper.delete_record(thread_id, br, html_file)
            if is_bug is None: return

        return is_bug

    def run(self) -> None:
        cur_mid = None
        hpr = self.helper

        while True:
            popped = hpr.pop_from_queue()
            if not popped: break

            result, vers = popped
            html_file, muts = result
            if len(muts) == 0:
                raise ValueError('Something wrong in muts...')

            start, end = vers
            if start >= end:
                print (html_file, 'start and end are the same;')
                continue

            start_idx = hpr.convert_to_index(start)
            end_idx = hpr.convert_to_index(end)

            if start_idx + 1 == end_idx:
                if self.cross_version_test(vers, html_file, muts):
                    hpr.update_postq(vers, html_file, muts)
                continue

            mid_idx = (start_idx + end_idx) // 2
            mid = hpr.convert_to_ver(mid_idx)
            self.cur_mid = mid
            if cur_mid != mid:
                cur_mid = mid
                self.get_browser(cur_mid)
                if not self.start_ref_browser(cur_mid):
                    continue

            is_bug = self.metamor_test(html_file, muts)
            if is_bug is None:
                mid_prev = hpr.convert_to_ver(mid_idx - 1)
                mid_next = hpr.convert_to_ver(mid_idx + 1)
                vers1 = (start, mid_prev)
                vers2 = (mid_next, end)
                if self.cross_version_test(vers1, html_file, muts):
                    hpr.insert_to_queue(vers1, html_file, muts)
                if self.cross_version_test(vers2, html_file, muts):
                    hpr.insert_to_queue(vers2, html_file, muts)
                continue

            elif not is_bug:
                if mid_idx + 1 == end_idx:
                    u_vers = (mid, end)
                    if self.cross_version_test(u_vers, html_file, muts):
                        hpr.update_postq(u_vers, html_file, muts)
                        #print (html_file, mid, end, 'postq 1')
                    continue
                low = hpr.convert_to_ver(mid_idx)
                high = end

            else:
                if mid_idx - 1 == start_idx:
                    u_vers = (start, mid)
                    if self.cross_version_test(u_vers, html_file, muts):
                        hpr.update_postq(u_vers, html_file, muts)
                        #print (html_file, start, mid, 'postq 2')
                    continue
                low = start
                high = hpr.convert_to_ver(mid_idx)

            hpr.insert_to_queue((low, high), html_file, muts)

        self.stop_ref_browser()


class Minimizer(CrossVersion):
    def __init__(self, helper: IOQueue, browser_type: str) -> None:
        CrossVersion.__init__(self, helper, browser_type)

        self.__min_html = None
        self.__html_file = None
        self.__temp_file = None
        self.__trim_file = None

        self.__js_file = None


    def __remove_temp_files(self):
        os.remove(self.__temp_file)
        os.remove(self.__trim_file)

    def __initial_test(self, html_file: str):

        self.__html_file = html_file
        self.__trim_file = join(dirname(html_file),
                'trim' + basename(html_file))
        self.__temp_file = join(dirname(html_file),
                'temp' + basename(html_file))

        copyfile(html_file, self.__trim_file)
        copyfile(html_file, self.__temp_file)

        self.__js_file = html_file.replace('.html', '.js')

        self.__min_html = FileManager.read_file(html_file)
        self.__muts = FileManager.read_js_file(self.__js_file)
        return self.cross_version_test_html(html_file, self.__muts)

    def __minimize_sline(self, idx, style_lines):
        style_line = style_lines[idx]

        style_line = re.sub('{ ', '{ \n', style_line)
        style_line = re.sub(' }', ' \n}', style_line)
        style_line = re.sub('; ', '; \n', style_line)
        style_blocks = style_line.split('\n')

        min_blocks = style_blocks
        min_indices = range(len(style_blocks))

        trim_sizes = [ pow(2,i) for i in range(3,-1,-1) ]
        trim_sizes = [x for x in trim_sizes if x < len(style_blocks)]
        for trim_size in trim_sizes:
            for offset in range(1, len(style_blocks) - 2, trim_size):
                if offset not in min_indices:
                    continue

                trim_indices = range(offset, min(offset + trim_size, len(style_blocks) - 2))

                tmp_blocks = []
                tmp_indices = []
                for i, line in enumerate(style_blocks):
                    if i not in trim_indices and i in min_indices:
                        tmp_blocks.append(style_blocks[i])
                        tmp_indices.append(i)

                last_block =  tmp_blocks[-1]
                if last_block[-2:] == '; ':
                    tmp_blocks[-1] = last_block[:-2] + ' '

                tmp_line = ''.join(tmp_blocks) + '\n'

                style_lines[idx] = tmp_line

                tmp_html = re.sub(re.compile(r'<style>.*?</style>', re.DOTALL), \
                                  '<style>' + ''.join(style_lines) + '</style>', self.__cat_html)

                FileManager.write_file(self.__trim_file, tmp_html)

                if self.cross_version_test_html(self.__trim_file, self.__muts):
                    min_blocks = tmp_blocks
                    min_indices = tmp_indices
                    FileManager.write_file(self.__temp_file, tmp_html)

        min_line = ''.join(min_blocks) + '\n'
        return min_line

    def __minimize_slines(self, style):
        style_content = style.contents[0]
        style_lines = [ line + '\n' for line in style_content.split('\n') if '{ }' not in line]

        min_lines = style_lines
        for i in range(len(style_lines)):
            if 'DO NOT REMOVE' in style_lines[i]: 
                break
            min_line = self.__minimize_sline(i, min_lines)
            min_lines[i] = min_line

        min_style = '<style>\n' + ''.join(min_lines) + '</style>'
        return min_style

    def __minimize_style(self):
        self.__cat_html = self.__min_html
        soup = BeautifulSoup(self.__cat_html, "lxml")
        if soup.style is not None and soup.style != " None":
            try:
                min_style = self.__minimize_slines(soup.style)
                self.__cat_html = re.sub(re.compile(r'<style>.*?</style>', re.DOTALL), \
                                       min_style, self.__cat_html)

                self.__min_html = self.__cat_html
            except:
                return
        else:
            return True

    def __minimize_dom(self):
        br = self.get_newer_browser()
        br.run_html(self.__temp_file)
        attrs = br.get_dom_tree_info()
        if not attrs: return

        for i in reversed(range(len(attrs))):
            br.run_html(self.__temp_file)
            br.exec_script(f'document.body.querySelectorAll(\'*\')[{i}].remove();')

            text = br.get_source()
            if not text: continue
            FileManager.write_file(self.__trim_file, text)
            br.clean_html()
            if self.cross_version_test_html(self.__trim_file, self.__muts):
                self.__min_html = text
                FileManager.write_file(self.__temp_file, self.__min_html)
            else:
                for attr in attrs[i]:
                    br.run_html(self.__temp_file)
                    br.exec_script(
                            f'document.body.querySelectorAll(\'*\')[{i}].removeAttribute(\'{attr}\');')
    
                    text = br.get_source()
                    if not text: continue
                    FileManager.write_file(self.__trim_file, text)
                    br.clean_html()
                    if self.cross_version_test_html(self.__trim_file, self.__muts):
                        self.__min_html = text
                        FileManager.write_file(self.__temp_file, self.__min_html)

    def __minimize_inner_element(self):
        br = self.get_newer_browser()
        br.run_html(self.__temp_file)
        attrs = br.get_dom_tree_info()
        if not attrs: return

        for i in reversed(range(len(attrs))):
            br.run_html(self.__temp_file)
            br.exec_script(
                f'temp1 = document.body.querySelectorAll(\'*\')[{i}];'.format(i) +
                'if (temp1.nextElementSibling) {' +
                'temp1.parentNode.append(...temp1.childNodes, temp1.nextElementSibling);}' +
                'else { temp1.parentNode.append(...temp1.childNodes);} ' + 
                'temp1.remove();'
            )

            text = br.get_source()
            if not text: continue
            FileManager.write_file(self.__trim_file, text)
            br.clean_html()
            if self.cross_version_test_html(self.__trim_file, self.__muts):
                self.__min_html = text
                FileManager.write_file(self.__temp_file, self.__min_html)

    def __minimize_text(self):
        br = self.get_newer_browser()
        br.run_html(self.__temp_file)
        attrs = br.get_dom_tree_info()
        if not attrs: return

        for i in reversed(range(len(attrs))):
            br.run_html(self.__temp_file)
            br.exec_script(f'document.body.querySelectorAll(\'*\')[{i}].textContent = \'\';')
            text = br.get_source()
            if not text: continue
            FileManager.write_file(self.__trim_file, text)
            br.clean_html()
            if self.cross_version_test_html(self.__trim_file, self.__muts):
                self.__min_html = text
                FileManager.write_file(self.__temp_file, self.__min_html)

    def __minimize_js(self):
        muts = self.__muts.copy()
        for i in reversed(range(len(muts))):
            removed = muts.pop(i)
            if self.cross_version_test_html(self.__temp_file, muts):
                self.__muts.pop(i)
            else:
                muts.insert(i, removed)


    def __minimizing(self):
        self.__minimize_js()
        self.__minimize_style()
        self.__minimize_dom()
        self.__minimize_text()
        self.__minimize_inner_element()


    def run(self) -> None:
        cur_vers = None
        hpr = self.helper
        while True:
            popped = hpr.pop_from_queue()
            if not popped: break

            result, vers = popped
            html_file, muts = result

            if cur_vers != vers:
                cur_vers = vers
                if not self.start_browsers(cur_vers):
                    continue

            if self.__initial_test(html_file):
                self.__minimizing()
  
                if self.cross_version_test_html(self.__temp_file, self.__muts):
                    orig_html_file = os.path.splitext(html_file)[0] + '-orig.html'
                    os.rename(html_file, orig_html_file) 
                    copyfile(self.__temp_file, html_file)
                    hpr.update_postq(vers, html_file, self.__muts)

            self.__remove_temp_files()

        self.stop_browsers()

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
            SingleVersion,
            CrossVersion,
            Minimizer,
            Bisecter,
        ]
        self.report = [
            CrossVersion,
        ]


    def skip_minimizer(self):
        self.tester.remove(Minimizer)

    def skip_bisecter(self):
        self.tester.remove(Bisecter)

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
            dir_path = os.path.join(self.out_dir, dirname)
            self.ioq.dump_queue(dir_path)


    def process(self) -> None:
        start = time.time()

        self.vm = VersionManager(self.browser_type)
        testcases = FileManager.get_all_files(self.in_dir, '.html')
        rev_range = self.vm.get_rev_range(self.base_ver, self.target_ver)


        num_of_tests = len(testcases)
        rev_a = rev_range[0]
        rev_b = rev_range[-1]

        print (f'# of tests: {num_of_tests}, rev_a: {rev_a}, rev_b: {rev_b}')

        self.ioq = IOQueue(testcases, rev_range)

        disp = Display(size=(1600, 1200))
        disp.start()

        for test in self.tester: 
            self.test_wrapper(test)

        elapsed = time.time() - start
        self.experiment_result['TOTAL TIME'] = str(timedelta(seconds=elapsed))

        if self.report:
            self.ioq.dump_queue_with_sort(os.path.join(self.out_dir, 'Report'))
            for test in self.report: 
                self.test_wrapper(test, True)

        disp.stop()
        print (self.experiment_result)


class Tester(Metamong):
    def __init__(self, input_dir: str, output_dir: str, num_of_threads: int,
                 browser_type:str, base_version: int, target_version: int) -> None:

        super().__init__(input_dir, output_dir, num_of_threads,
                         browser_type, base_version, target_version)
        self.tester = [
            SingleVersion,
            Minimizer
        ]
        self.report = [
            SingleVersion
        ]
