import copy
import time
import bisect
import numpy as np

from queue import Queue
from pathlib import Path
from random import choice
from threading import Lock
from threading import Semaphore
from typing import Optional, Tuple
from shutil import copyfile
from collections import defaultdict

from firefox_binary import build_firefox_binary
from chrome_binary import build_chrome_binary
from chrome_binary import get_commit_from_position

from contextlib import contextmanager

from PIL import Image
from io import BytesIO
from os import walk, listdir, getenv
from os.path import join, dirname, abspath, exists, basename
from chrome_binary import ChromeBinary

@contextmanager
def acquire_timeout(lock, timeout):
    result = lock.acquire(timeout=timeout)
    yield result
    if result:
        lock.release()

MILESTONE = {
    79: 706915,
    80: 722274,
    81: 737173,
    82: 749737,
    83: 756066,
    84: 768962,
    85: 782793,
    86: 800218,
    87: 812852,
    88: 827102,
    89: 843830,
    90: 857950,
    91: 870763,
    92: 885287,
    93: 902210,
    94: 911515,
    95: 920003,
    96: 929512,
    97: 938553,
    98: 950365,
    99: 961656,
    100: 972766,
    101: 982481,
    102: 992738,
    103:1002911,
    104:1012729,
    105:1027018,
    106:1036826,
    107:1047731,
}

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def printf(color, p):
    bc = ''
    if color == 'WARNING':
        bc = bcolors.WARNING
    elif color == 'GREEN':
        bc = bcolors.OKGREEN
    elif color == 'FAIL':
        bc = bcolors.FAIL
    else:
        bc = bcolors.OKBLUE
    print (f'{bc}{p}{bcolors.ENDC}')


class IOQueue:
    def __init__(self, testcases: list, revision_range: list) -> None:

        self.__queue_lock = Lock()
        self.__build_lock = Semaphore(1)

        self.__download_sem = Semaphore(8)
        self.__download_locks = {}

        self.__preqs = defaultdict(Queue)
        self.__postqs = defaultdict(Queue)
        self.__vers = None

        self.num_of_tests = 0
        self.num_of_inputs = 0
        self.num_of_outputs = 0

        limit = getenv('LIMIT')
        self.limit = 100000 if not limit else int(limit)

        self.version_list = {}
        self.monitor = defaultdict(float)

        self.revlist = revision_range
        for rev in self.revlist:
            self.__download_locks[rev] = Lock()

        vers = (self.revlist[0], self.revlist[-1])
        for testcase in testcases:
            js = testcase.replace('.html', '.js')
            muts = FileManager.read_file(js).split('\n') if exists(js) else []
            self.insert_to_queue(vers, testcase, muts)

        self.start_time = time.time()

    def reset_lock(self):
        if self.__queue_lock.locked():
            self.__queue_lock.release()

    def download_chrome(self, commit_version: int) -> None:
        self.__download_sem.acquire()
        browser_type = 'chrome'
        parent_dir = FileManager.get_parent_dir(__file__)
        browser_dir = join(parent_dir, browser_type)
        self.__download_locks[commit_version].acquire()
        cb = ChromeBinary()
        cb.ensure_chrome_binaries(browser_dir, commit_version)
        self.__download_locks[commit_version].release()
        self.__download_sem.release()

    def build_chrome(self, commit_version: int) -> None:
        browser_type = 'chrome'
        self.__build_lock.acquire()
        parent_dir = FileManager.get_parent_dir(__file__)
        browser_dir = join(parent_dir, browser_type)
        browser_path = join(browser_dir, str(commit_version), browser_type)
        if not exists(browser_path):
            build_chrome_binary(commit_version)
        self.__build_lock.release()

    def build_firefox(self, commit_version: int) -> None:
        browser_type = 'firefox'
        self.__build_lock.acquire()
        parent_dir = FileManager.get_parent_dir(__file__)
        browser_dir = join(parent_dir, browser_type)
        browser_path = join(browser_dir, str(commit_version), browser_type)
        if not exists(browser_path):
            build_firefox_binary(commit_version)
        self.__build_lock.release()

    def __select_vers(self) -> Optional[Tuple[int, int, int]]:
        keys = list(self.__preqs.keys())
        key =  choice(keys) if keys else None
        return key


    def insert_to_queue(self, vers: Tuple[int, int, int], html_file: str, muts: list) -> None:
        with acquire_timeout(self.__queue_lock, -1) as acquired:
            if not acquired: return 
            value = [html_file, muts]
            self.__preqs[vers].put(value)
            self.num_of_inputs += 1

            if not self.__vers: 
                self.__vers = self.__select_vers()

    def pop_from_queue(self, use_limit=True) -> Optional[list]:
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            value = None
            if not self.__vers: 
                return
            if use_limit and self.num_of_outputs >= self.limit:
                self.__preqs.clear()
                self.__vers = self.__select_vers()
                return 
        
            vers = self.__vers
            value = self.__preqs[vers].get()
            if self.__preqs[vers].empty():
                self.__preqs.pop(vers)
                self.__vers = self.__select_vers()
            self.num_of_tests += 1
            if self.num_of_tests % 100 == 0:
                tt = round((time.time() - self.start_time) / 60, 3)
                ot = round(self.num_of_tests / tt, 3)
                printf('BLUE', f'test: {self.num_of_tests}, outputs: {self.num_of_outputs}, time: {tt}, test / time: {ot}')
            return value, vers

    def get_vers(self) -> Optional[Tuple[int, int, int]]:
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            vers = self.__vers
            return vers

    def update_postq(self, vers: Tuple[int, int, int], html_file: str, muts: list) -> None:
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            self.__postqs[vers].put((html_file, muts))
            self.num_of_outputs += 1
            if self.num_of_outputs % 20 == 0:
                tt = round((time.time() - self.start_time) / 60, 3)
                ot = round(self.num_of_tests / tt, 3)
                printf('GREEN', f'test: {self.num_of_tests}, outputs: {self.num_of_outputs}, time: {tt}, test / time: {ot}')

    def move_to_preqs(self):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            self.__preqs.clear()
            self.__preqs = self.__postqs.copy()
            self.__postqs.clear()
            self.__vers = self.__select_vers()
            self.num_of_inputs = self.num_of_outputs
            self.num_of_tests = 0
            self.num_of_outputs = 0

    def dump_queue(self, dir_path):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 

            Path(dir_path).mkdir(parents=True, exist_ok=True)
            keys = list(self.__preqs.keys())
            for vers in keys:
                q = self.__preqs[vers]
                length = len(list(q.queue))
                for _ in range(length):
                    html_file, muts = q.get()
                    name = basename(html_file)
                    new_html_file = join(dir_path, name)
                    copyfile(html_file, new_html_file)
                    new_js_file = join(dir_path, name.replace('.html', '.js'))
                    FileManager.write_file(new_js_file, '\n'.join(muts))
                    q.put((new_html_file, muts))
    

    def dump_queue_as_csv(self, path):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            path = join(path, 'result.csv')
            with open(path, 'w') as csvfile:
                header = ['base', 'target', 'ref', 'file']
                csvfile.write(','.join(header))
                csvfile.write('\n')
                keys = sorted(list(self.__preqs.keys()))
                for key in keys:
                    q = self.__preqs[key]
                    for value in sorted(list(q.queue)):
                        html_file, muts = value
                        base, target, ref = key
                        csvfile.write(f'{base}, {target}, {ref}, {html_file}\n')

    def dump_queue_with_sort(self, dir_path):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            keys = sorted(list(self.__preqs.keys()))
            for vers in keys:
                q = self.__preqs[vers]
                length = q.qsize()
                cur_path = join(dir_path, str(vers[1]))
                Path(cur_path).mkdir(parents=True, exist_ok=True)
                commit_a = get_commit_from_position(vers[0])
                commit_b = get_commit_from_position(vers[1])
                url = f'https://chromium.googlesource.com/chromium/src/+log/{commit_a}..{commit_b}'
                FileManager.write_file(join(cur_path, 'changelog.txt'), url)
                for _ in range(length):
                    html_file, muts = q.get()
                    name = basename(html_file)
                    new_html_file = join(cur_path, name)
                    copyfile(html_file, new_html_file)
                    new_js_file = join(cur_path, name.replace('.html', '.js'))
                    FileManager.write_file(new_js_file, '\n'.join(muts))
                    q.put((new_html_file, muts))

    def set_version_list(self, html_file, build) -> None:
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            if html_file not in self.version_list:
                if not build:
                    verlist = copy.deepcopy(self.revlist)
                else:
                    verlist = list(range(self.revlist[0], self.revlist[-1] + 1))
                self.version_list[html_file] = verlist

    def convert_to_ver(self, html_file, index: int) -> int:
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            return self.version_list[html_file][index]

    def convert_to_index(self, html_file, version: int) -> int:
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return 
            verlist = self.version_list[html_file]
            index = bisect.bisect_left(verlist, version) 
            if index != len(verlist) and verlist[index] == version:
                return index

            print ('no index found', html_file, index)
            return -1

    def pop_index_from_list(self, html_file, index):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return
            v = self.version_list[html_file][index]
            del self.version_list[html_file][index]
            print ('version delete', html_file, index, v)


    def record_current_test(self, thread_id, br, html_file):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return
            self.monitor[(thread_id, br.version, html_file)] = (br, time.time())

    def delete_record(self, thread_id, br, html_file):
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return
            self.monitor.pop((thread_id, br.version, html_file), None)

    def monitoring(self):
        brs = []
        with acquire_timeout(self.__queue_lock, 1000) as acquired:
            if not acquired: return
            cur_time = time.time()
            for cur_test in self.monitor:
                br, t = self.monitor[cur_test]
                if cur_time - t > 30:
                    brs.append(br)
                    printf ('WARNING', f'Chrome {cur_test[1]} in thread {cur_test[0]} is hanging ... {cur_test[2]}')

        for br in brs:
            br.kill_browser_by_pid()

class FileManager:
    def get_all_files(root, ext=None) -> list:
        paths = []
        for path, subdirs, files in walk(root):
            for name in files:
                if ext is not None and ext not in name:
                    continue
                paths.append((join(path, name)))
        return paths

    def get_parent_dir(file):
        return dirname(dirname(abspath(file)))

    def write_file(name, content):
        with open(name, 'w') as fp:
            fp.write(content)

    def read_file(name):
        with open(name, 'r') as fp:
            return fp.read()

class VersionManager:
    def __init__(self):
        csvfile = join(
                dirname(dirname(abspath(__file__))),
                'data', 
                'bisect-builds-cache.csv')
        self.revlist = []
        with open(csvfile, 'r') as fp:
            line = fp.readline()
            vers = line.split(', ')
            for ver in vers:
                v = int(ver)
                self.revlist.append(v)
        self.revlist.sort()

    def get_revision(self, version):
        return self.revlist[bisect.bisect_left(self.revlist, MILESTONE[version - 1]) - 1]

    def get_end_revision(self, version):
        return self.revlist[bisect.bisect_left(self.revlist, MILESTONE[version]) - 1]

    def get_rev_range(self, a, b):
        tmp = []
        rev_a = self.get_revision(a)
        rev_b = self.get_revision(b)
        for rev in self.revlist:
            if rev_a <= rev <= rev_b:
                tmp.append(rev)
        return tmp

import hashlib
from imagehash import phash
class ImageDiff:
    def get_hash(png):
        stream = png if isinstance(png, str) else BytesIO(png)
        try:
            with Image.open(stream, 'r') as image:
                pixel = np.asarray(image)
                return hashlib.sha1(pixel).hexdigest()
        except Exception as e:
            print (e)

    def get_phash(png):
        stream = png if isinstance(png, str) else BytesIO(png)
        try:
            with Image.open(stream, 'r') as image:
                return phash(image, hash_size=16)
        except Exception as e:
            print (e)

    def diff_images(hash_A, hash_B, phash=False):
        if phash:
            return hash_A - hash_B >= 16
        else:
            return hash_A != hash_B

    def save_image(name, png):
        try:
            stream = BytesIO(png)
            im = Image.open(stream, 'r')
            im.save(name)
            im.close()
        except Exception as e:
            print (e)

