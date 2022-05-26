import os
import re

from driver import Browser
from typing import Optional

from helper import IOQueue
from helper import ImageDiff
from helper import FileManager
from threading import Thread

from bisect import bisect

from pathlib import Path
from shutil import copyfile
from bs4 import BeautifulSoup

from jshelper import GET_ATTRNAMES


class CrossVersion(Thread):
    def __init__(self, helper: IOQueue) -> None:
        super().__init__()
        self.__br_list = []

        self.helper = helper
        self.saveshot = False
        self.fnr = False

    def report_mode(self) -> None:
        self.saveshot = True
        self.fnr = True

    def get_newer_browser(self) -> Browser:
        return self.__br_list[-1] if self.__br_list else None

    def start_browsers(self, vers: tuple[int, int, int]) -> bool:
        self.stop_browsers()
        self.__br_list.append(Browser('chrome', vers[0]))
        self.__br_list.append(Browser('chrome', vers[1]))
        for br in self.__br_list:
            if not br.setup_browser():
                return False
        return True

    def stop_browsers(self) -> None:
        for br in self.__br_list: br.kill_browser()
        self.__br_list.clear()

    def cross_version_test_html(self, html_file: str, fn_reduction: bool = False) -> Optional[list]:
        img_hashes = []
        for br in self.__br_list:
            hash_v = br.get_hash_from_html(html_file, self.saveshot, fn_reduction)
            if not hash_v: 
                print ('something wrong?')
                return

            img_hashes.append(hash_v)

        return img_hashes

    def is_bug(self, hashes):
        return  hashes and ImageDiff.diff_images(hashes[0], hashes[1])

    def run(self) -> None:

        cur_vers = None
        hpr = self.helper
        while True:
            vers = hpr.get_vers()
            if not vers: break

            result = hpr.pop_from_queue()
            if not result: break
            html_file, _ = result

            if cur_vers != vers:
                cur_vers = vers

                hpr.download_chrome(cur_vers[0])
                hpr.download_chrome(cur_vers[1])
                if not self.start_browsers(cur_vers):
                    continue


            hashes = self.cross_version_test_html(html_file, self.fnr)
            if self.is_bug(hashes):
                hpr.update_postq(vers, html_file, hashes)

        self.stop_browsers()


class Oracle(Thread):
    def __init__(self, helper: IOQueue) -> None:
        super().__init__()
        self.helper = helper
        self.ref_br = None
        self.saveshot = False

    def start_ref_browser(self, ver: int) -> bool:
        self.stop_ref_browser()
        self.ref_br = Browser('firefox', ver)
        return self.ref_br.setup_browser()

    def stop_ref_browser(self):
        if self.ref_br:
            self.ref_br.kill_browser()
            self.ref_br = None

    def is_regression(self, hashes: tuple, ref_hash) -> bool:
        #return hashes[0] != hashes[1] and hashes[0] == ref_hash
        return hashes[0] == ref_hash


    def run(self) -> None:

        cur_refv = None
        hpr = self.helper
        while True:
            vers = hpr.get_vers()
            if not vers: break

            result = hpr.pop_from_queue()
            if not result: break
            html_file, hashes = result
            if len(hashes) != 2:
                raise ValueError('Something wrong in hashes...')

            refv = vers[-1]
            if cur_refv != refv:
                cur_refv = refv
                if not self.start_ref_browser(cur_refv):
                    continue

            ref_hash = self.ref_br.get_hash_from_html(html_file, self.saveshot, True)
            if ref_hash and self.is_regression(hashes, ref_hash):
                hpr.update_postq(vers, html_file, hashes)

        self.stop_ref_browser()


class Bisecter(Thread):
    def __init__(self, helper: IOQueue) -> None:
        super().__init__()
        self.helper = helper
        self.ref_br = None
        self.__version_list = []
        self.saveshot = False

    def start_ref_browser(self, ver: int) -> bool:
        self.stop_ref_browser()
        self.ref_br = Browser('chrome', ver)
        return self.ref_br.setup_browser()

    def stop_ref_browser(self) -> None:
        if self.ref_br:
            self.ref_br.kill_browser()
            self.ref_br = None

    def set_version_list(self) -> None:
        self.__version_list = FileManager.get_bisect_csv()

    def convert_to_ver(self, index: int) -> int:
        return self.__version_list[index]

    def convert_to_index(self, ver: int) -> int:
        return bisect(self.__version_list, ver) 

    def get_chrome(self, ver: int) -> None:
        self.helper.download_chrome(ver)

    def run(self) -> None:
        cur_mid = None
        hpr = self.helper
        self.set_version_list()

        while True:
            vers = hpr.get_vers()
            if not vers: break

            result = hpr.pop_from_queue()
            if not result: break
            html_file, hashes = result
            if len(hashes) != 2:
                raise ValueError('Something wrong in hashes...')


            start, end, ref = vers
            if start >= end: continue

            start_idx = self.convert_to_index(start)
            end_idx = self.convert_to_index(end)

            if end_idx - start_idx == 1:
                hpr.update_postq(vers, html_file, hashes)
                continue

            mid_idx = (start_idx + end_idx) // 2
            mid = self.convert_to_ver(mid_idx)
            if cur_mid != mid:
                cur_mid = mid
                self.get_chrome(cur_mid)
                if not self.start_ref_browser(cur_mid):
                    continue

            ref_hash = self.ref_br.get_hash_from_html(html_file, self.saveshot, True)
            if not ref_hash: continue

            if hashes[0] == ref_hash:
                low = self.convert_to_ver(mid_idx + 1)
                high = end

            elif hashes[1] == ref_hash:
                low = start
                high = self.convert_to_ver(mid_idx - 1)
            else:
                print (html_file, 'is skipped;')
                continue

            hpr.insert_to_queue((low, high, ref), html_file, hashes)

        self.stop_ref_browser()


class BisecterBuild(Bisecter):
    def __init__(self, helper: IOQueue) -> None:
        super().__init__(helper)

    def set_version_list(self) -> None:
        pass

    def convert_to_ver(self, index: int) -> int:
        return index

    def convert_to_index(self, ver: int) -> int:
        return ver

    def get_chrome(self, ver: int) -> None:
        self.helper.build_chrome(ver)


class Minimizer(CrossVersion):
    def __init__(self, helper: IOQueue) -> None:
        CrossVersion.__init__(self, helper)

        self.__min_html = None
        self.__html_file = None
        self.__temp_file = None
        self.__trim_file = None


    def __remove_temp_files(self):
        os.remove(self.__temp_file)
        os.remove(self.__trim_file)

    def __initial_test(self, html_file):

        self.__html_file = html_file
        self.__trim_file = os.path.join(os.path.dirname(html_file), 
                'trim' + os.path.basename(html_file))
        self.__temp_file = os.path.join(os.path.dirname(html_file), 
                'temp' + os.path.basename(html_file))

        copyfile(html_file, self.__trim_file)
        copyfile(html_file, self.__temp_file)

        self.__min_html = FileManager.read_file(html_file)
        hashes = self.cross_version_test_html(html_file) 
        return self.is_bug(hashes)


    def __minimize_sline(self, idx, style_lines):
        style_line = style_lines[idx]

        style_line = re.sub('{ ', '{ \n', style_line)
        style_line = re.sub(' }', ' \n}', style_line)
        style_line = re.sub('; ', '; \n', style_line)
        style_blocks = style_line.split('\n')

        #print('> Minimizing style idx: {} ...'.format(idx))
        #print('> Initial style entries: {}'.format(len(style_blocks)))

        min_blocks = style_blocks
        min_indices = range(len(style_blocks))

        trim_sizes = [ pow(2,i) for i in range(3,-1,-1) ] # 8, 4, 2, 1
        trim_sizes = [x for x in trim_sizes if x < len(style_blocks)]
        for trim_size in trim_sizes:
            #print('> Setting trim size: {}'.format(trim_size))
            for offset in range(1, len(style_blocks) - 2, trim_size):
                if offset not in min_indices:
                    continue
                #print('> Current style entries: {}'.format(len(min_blocks)))

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
                                  '<style>\n' + ''.join(style_lines) + '\n</style>', self.__cat_html)

                FileManager.write_file(self.__trim_file, tmp_html)

                hashes = self.cross_version_test_html(self.__trim_file)
                if self.is_bug(hashes):
                    min_blocks = tmp_blocks
                    min_indices = tmp_indices
                    FileManager.write_file(self.__temp_file, tmp_html)

        min_line = ''.join(min_blocks) + '\n'
        return min_line

    def __minimize_slines(self, style):
        style_content = style.contents[0]
        style_lines = [ line + '\n' for line in style_content.split('\n') if '{ }' not in line]
        #print (style_lines)

        min_lines = style_lines
        for i in range(len(style_lines) - 4):
            min_line = self.__minimize_sline(i, min_lines)
            min_lines[i] = min_line

        min_style = '<style>\n' + ''.join(min_lines) + '\n</style>'
        return min_style

    def __minimize_style(self):
        self.__cat_html = self.__min_html
        soup = BeautifulSoup(self.__cat_html, "lxml")
        if soup.style is not None and soup.style != " None":
            try:
                min_style = self.__minimize_slines(soup.style)
                self.__cat_html = re.sub(re.compile(r'<style>.*?</style>', re.DOTALL), \
                                       min_style, self.__cat_html)

                self.__min_html = [ line + '\n' for line in self.__cat_html.split('\n') ]
            except:
                #print ('style is ', soup.style)
                return
        else:
            return True

    def __minimize_dom(self):
        br = self.get_newer_browser()
        br.run_html(self.__temp_file)
        attrs = br.exec_script(GET_ATTRNAMES)
        if not attrs: return

        for i in range(len(attrs) - 1, 0, -1):
            br.run_html(self.__temp_file)
            br.exec_script(f'document.body.querySelectorAll(\'*\')[{i}].remove();')

            text = br.get_source()
            if not text: continue
            FileManager.write_file(self.__trim_file, text)
            hashes = self.cross_version_test_html(self.__trim_file) 
            if self.is_bug(hashes):
                #print (f'{i}th element is removed')
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
                    hashes = self.cross_version_test_html(self.__trim_file) 
                    if self.is_bug(hashes):
                        #print (f'{attr} attr is removed')
                        self.__min_html = text
                        FileManager.write_file(self.__temp_file, self.__min_html)


    def __minimizing(self):
        self.__minimize_dom()
        self.__minimize_style()


    def run(self) -> None:
        cur_vers = None
        hpr = self.helper
        while True:
            vers = hpr.get_vers()
            if not vers: break

            result = hpr.pop_from_queue()
            if not result: break
            html_file, _ = result

            if cur_vers != vers:
                cur_vers = vers
                if not self.start_browsers(cur_vers):
                    continue


            if self.__initial_test(html_file):
                self.__minimizing()

                hashes = self.cross_version_test_html(self.__temp_file, True)
                #print ('after', hashes[0] - hashes[1])
                min_html_file = os.path.splitext(html_file)[0] + '-min.html'
                copyfile(self.__temp_file, min_html_file)
                if self.is_bug(hashes):
                    hpr.update_postq(vers, min_html_file, hashes)

            self.__remove_temp_files()

        self.stop_browsers()


class R2Z2:
    def __init__(self, input_version_pair: dict[str, tuple[int, int, int]], output_dir: str, num_of_threads: int) -> None:
        self.ioq = IOQueue(input_version_pair)
        self.out_dir = output_dir
        self.num_of_threads = num_of_threads

    def test_wrapper(self, test_class: object, report: bool = False) -> None:
        threads = []
        for i in range(self.num_of_threads):
            threads.append(test_class(self.ioq))
            threads[-1].saveshot = report

        class_name = type(threads[-1]).__name__
        print (f'{class_name} stage starts...')

        dirname = class_name if not report else 'Report'

            

        for th in threads:
            if report: th.report_mode()
            th.start()

        for th in threads:
            th.join()

        dir_path = os.path.join(self.out_dir, dirname)
        if not report:
            self.ioq.dump_queue(dir_path)
        self.ioq.dump_queue_as_csv(os.path.join(dir_path, 'result.csv'))
        self.ioq.move_to_preqs()


    def process(self) -> None:
        tester = [
                CrossVersion,
                Minimizer,
                Oracle,
                Bisecter,
                BisecterBuild
        ]

        for test in tester: 
            self.test_wrapper(test)

        self.ioq.dump_queue_with_sort(os.path.join(self.out_dir, 'Report'))

        report = [
                CrossVersion,
        ]

        for test in report: 
            self.test_wrapper(test, True)



class Finder(R2Z2):
    def __init__(self, input_version_pair: dict[str, tuple[int, int, int]], output_dir: str, num_of_threads: int, answer_version: int) -> None:
        super().__init__(input_version_pair, output_dir, num_of_threads)
        self.__answer_version = answer_version


    def answer(self) -> None:
        print ('answer step')
        ref_br = Browser('chrome', self.__answer_version)
        ref_br.setup_browser()

        hpr = self.ioq
        while True:
            vers = hpr.get_vers()
            if not vers: break

            result = hpr.pop_from_queue()
            if not result: break
            html_file, hashes = result
            if len(hashes) != 2:
                raise ValueError('Something wrong in hashes...')

            ref_hash = ref_br.get_hash_from_html(html_file, True, True)
            if ref_hash and hashes[0] == ref_hash:
                hpr.update_postq(vers, html_file, hashes)

        ref_br.kill_browser()
        dir_path = os.path.join(self.out_dir, 'answer')
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        self.ioq.dump_queue_as_csv(os.path.join(dir_path, 'result.csv'))


    def process(self) -> None:
        tester = [
                CrossVersion,
                Minimizer,
                Oracle,
                Bisecter,
        ]

        for test in tester: 
            self.test_wrapper(test)

        self.ioq.dump_queue_with_sort(os.path.join(self.out_dir, 'Report'))

        report = [
                CrossVersion,
        ]

        for test in report: 
            self.test_wrapper(test, True)

        self.answer()
