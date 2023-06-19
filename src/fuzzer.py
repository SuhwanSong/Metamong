from os import remove, environ, kill
from os.path import join, exists

from mutater import MetaMut
from typing import Optional, Tuple

from threading import Thread
from threading import current_thread, get_native_id

from utils.driver import Browser
from utils.helper import IOQueue
from utils.helper import FileManager

from pyvirtualdisplay import Display

class Fuzzer(Thread):
    def __init__(self, id_: int, helper: IOQueue, browser_type: str) -> None:
        super().__init__()

        self.br_list = []

        self.__id = id_
        self.helper = helper
        self.__btype = browser_type

        self.report_mode = False
        self.saveshot = False
        self.iter_num = 4

        self.__cross_version = False

        self.meta_mut = MetaMut()

    def cross_version_mode(self) -> None:
        self.__cross_version = True

    def report_mode(self) -> None:
        self.report_mode = True
        self.saveshot = True
        self.iter_num = 1

    def get_older_browser(self) -> Browser:
        return self.br_list[0] if self.br_list else None

    def get_newer_browser(self) -> Browser:
        return self.br_list[-1] if self.br_list else None

    def start_browsers(self, vers: Tuple[int, int], vid: str = '') -> bool:
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
            self.br_list.append(Browser(bt, ver, popup=True, vid_=vid))

        for br in self.br_list:
            if not br.setup_browser():
                return False
        return True

    def stop_browsers(self) -> None:
        for br in self.br_list:
            br.kill_browser()
        self.br_list.clear()

    def __test_wrapper(self, br, html_file: str, muts: list, phash: bool = False):
        thread_id = current_thread()
        self.helper.record_current_test(thread_id, br, html_file)
        is_bug = br.metamor_test(html_file, muts, save_shot=self.saveshot, phash=phash)
        self.helper.delete_record(thread_id, br, html_file)
        return is_bug

    def gen_muts(self, html_file: str, muts: list):
        br = self.get_newer_browser()
        dic = br.analyze_html(html_file)
        if not dic: return
        self.meta_mut.load_state(dic)
        muts.extend(self.meta_mut.generate())

    def test_html(self, html_file: str, muts: list, phash: bool = False):
        br = self.get_newer_browser()
        for _ in range(self.iter_num):
            is_bug = self.__test_wrapper(br, html_file, muts, phash=phash)
            if is_bug is not None: self.helper.count_valid_test()
            if is_bug is None or not is_bug: return False

        # if not cross_version test mode, return true
        if not self.__cross_version: return True

        # cross-version test, old one should not have a bug, using hash
        old_br = self.get_older_browser()
        for _ in range(self.iter_num):
            is_bug = self.__test_wrapper(old_br, html_file, muts)
            if is_bug is None or is_bug: return False

        return True

    def run(self) -> None:

        cur_vers = None
        hpr = self.helper
        if environ.get('DEBUG'):
            vdisplay = Display(size=(1600, 1200), backend="xvnc", rfbport=self.__id + 5900)
        else:
            vdisplay = Display(size=(1600, 1200))
        vdisplay.start()
        env = vdisplay.new_display_var
        try:
            while True:
                popped = hpr.pop_from_queue()
                if not popped: break
    
                result, vers = popped
                html_file, muts = result
    
                if cur_vers != vers:
                    cur_vers = vers
                    ver = cur_vers[-1]
                    if not self.start_browsers([ver], env):
                        continue
    
                # This is for eliminating non-invalidation bug.
                br = self.get_newer_browser()
                if self.__test_wrapper(br, html_file, [], phash=True):
                    continue
    
                if not muts:
                    self.gen_muts(html_file, muts)
                    #FileManager.write_file(html_file.replace('.html', '.js'), '\n'.join(muts))
                     
                if self.test_html(html_file, muts, phash=True):
                    hpr.update_postq(vers, html_file, muts)

        finally:
            vdisplay.stop()
            self.stop_browsers()
