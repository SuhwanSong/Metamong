import sys
import time, psutil
from pathlib import Path
from helper import ImageDiff
from helper import FileManager

from selenium import webdriver
from collections import defaultdict

from os import environ
from os.path import dirname, join, abspath, splitext, exists

from chrome_binary import ChromeBinary
from firefox_binary import FirefoxBinary

GET_ATTRNAMES="""
let attrs = [];
const elements = document.body.querySelectorAll('*');
for (var i = 0; i < elements.length; i++) {
  attrs.push(elements[i].getAttributeNames());
}
return attrs;
"""

GET_PAGE="""return window.SC.get_page();"""

class Browser:
    def __init__(self, browser_type: str, commit_version: int, flags: str = '') -> None:
        environ["DBUS_SESSION_BUS_ADDRESS"] = '/dev/null'

        self.__width = 800
        self.__height = 600

        browser_types = ['chrome', 'firefox']
        if browser_type not in browser_types:
            raise ValueError('[DEBUG] only chrome or firefox are allowed')

        self.browser = None
        self.__num_of_run = 0
        self.__browser_type = browser_type

        self.version = commit_version
        self.flags = []

        if flags:
            for flag in flags.split(' '):
                self.flags.append(flag)

    def __set_viewport_size(self):
        window_size = self.browser.execute_script("""
        return [window.outerWidth - window.innerWidth + arguments[0],
          window.outerHeight - window.innerHeight + arguments[1]];
        """, self.__width, self.__height)
        if window_size:
            self.browser.set_window_size(*window_size)

    # Due to https://github.com/mozilla/geckodriver/issues/1744, setting the
    # width/height of firefox includes some browser UI. This workaround is
    # needed to resize the browser contents so screenshots are the appropriate
    # size, rather than [height] - [ui height].
    def __adjust_viewport_size(self):
        width, height = self.exec_script('return [window.innerWidth, window.innerHeight]')
        self.browser.set_window_size(
                self.__width + (self.__width - width),
                self.__height + (self.__height - height))

    def __screenshot_and_hash(self, name=None, phash=False):
        png = self.get_screenshot()
        if name:
            ImageDiff.save_image(name, png)
        return ImageDiff.get_hash(png) if not phash else ImageDiff.get_phash(png)

    def __repeatly_run(self, html_file):
        for attempt in range(5):
            if attempt == 4:
                self.kill_browser()
                self.setup_browser()
            try:
                self.clean_html() 
                self.browser.get('file://' + abspath(html_file))
                return
            except Exception as e:
                continue

        return None

    def setup_browser(self):
        self.__num_of_run = 0
        self.browser = None
        parent_dir = FileManager.get_parent_dir(__file__)
        browser_dir = join(parent_dir, self.__browser_type)
        if not exists(browser_dir):
            Path(browser_dir).mkdir(parents=True, exist_ok=True)

        for _ in range(5):
            try:
                if self.__browser_type == 'chrome':
                    options = [
                            '--headless',
                            '--disable-seccomp-sandbox',
                            '--disable-logging',
                            '--disable-gpu',
                            f'--window-size={self.__width},{self.__height}',
                            ]
                    options.extend(self.flags)
                    option = webdriver.chrome.options.Options()
                    cb = ChromeBinary()
                    cb.ensure_chrome_binaries(browser_dir, self.version)

                    browser_path = cb.get_browser_path(browser_dir, self.version)
                    option.binary_location = browser_path
                    for op in options: option.add_argument(op)

                    driver_path = cb.get_driver_path(browser_dir, self.version)
                    self.browser = webdriver.Chrome(options=option,
                            executable_path=driver_path)
                elif self.__browser_type == 'firefox':
                    options = [
                            '--headless',
                            '--disable-gpu',
#                            f'--width={self.__width}',
#                            f'--height={self.__height}',
                            ]
                    option = webdriver.firefox.options.Options()
                    fb = FirefoxBinary()
                    if not fb.firefox_binary_exist(browser_dir, self.version):
                        print ('No firefox binaries...', self.version) 
                        sys.exit(1)
                        
                    browser_path = fb.get_browser_path(browser_dir, self.version)
                    option.binary_location = browser_path
                    for op in options: option.add_argument(op)

                    driver_path = fb.get_driver_path(browser_dir, self.version)
                    self.browser = webdriver.Firefox(options=option,
                            executable_path=driver_path)
                else:
                    raise ValueError('Check browser type')

                break

            except Exception as e:
                print (e)
                time.sleep(0.2)
                continue

        # System crashes if fails to start browser.
        if self.browser is None:
            print (f"Browser {self.version} fails to start..")
            sys.exit(1)

        for _ in range(5):
            try:
                platform = sys.platform
                platform_funcs = {'linux': self.__set_viewport_size,
                                  'darwin': self.__adjust_viewport_size, }
                platform_funcs[platform]()
                break
            except Exception as e:
                print (e)
                continue

        TIMEOUT = 10
        self.browser.set_script_timeout(TIMEOUT)
        self.browser.set_page_load_timeout(TIMEOUT)
        self.browser.implicitly_wait(TIMEOUT)

        return True

    def kill_browser(self):
        if self.browser and self.browser.session_id:
            try:
                self.browser.close()
                self.browser.quit()
            except:
                return False

        return True

    def kill_browser_by_pid(self):
        if not self.browser or self.__browser_type == 'firefox':
            return False
        br = self.browser
        if not br.session_id or not br.service or not br.service.process:
            return False
        try:
            p = psutil.Process(br.service.process.pid)
            for proc in p.children(recursive=True):
                proc.kill()
        except Exception as e:
            pass
        return True

    def get_source(self):
        try: return '<!DOCTYPE html>\n' + self.browser.page_source
        except: return

    def exec_script(self, scr, arg=None):
        try:
            return self.browser.execute_script(scr, arg)
        except Exception as e:
            return None

    def run_html(self, html_file: str):
        if self.__num_of_run == 1000:
            self.kill_browser()
            self.setup_browser()
        self.__repeatly_run(html_file)
        self.__num_of_run += 1
        return True

    def clean_html(self):
        self.browser.get('about:blank')

    def get_screenshot(self):
        for attempt in range(5):
            if attempt == 4:
                self.kill_browser()
                self.setup_browser()
            try:
                png = self.browser.get_screenshot_as_png()
                return png
            except Exception as e:
                continue

        return None

    def get_hash_from_html(self, html_file, save_shot: bool = False):
        ret = self.run_html(html_file)
        if not ret: return

        name_noext = splitext(html_file)[0]
        screenshot_name = f'{name_noext}_{self.version}.png' if save_shot else None
        hash_v = self.__screenshot_and_hash(screenshot_name)
        return hash_v

    def get_dom_tree_info(self):
        return self.exec_script(GET_ATTRNAMES)

    def analyze_html(self, html_file):
        dic = {}
        if not self.run_html(html_file): return dic

        scripts = {'ids': 'return get_all_ids();',
                   'attributes': 'return get_all_attributes();',
                   'css_length': 'return get_css_length();',
        }

        for key in scripts:
            dic[key] = self.exec_script(scripts[key])
            if not dic[key]: return {}
        return dic

    def __save_state(self):
        self.exec_script("window.SC = new window.StateChecker();")

    def __re_render(self):
        self.exec_script("window.SC.write_document();")

    def __is_same_state(self):
        return self.exec_script("return window.SC.is_same_state();")

    def metamor_test(self, html_file, muts, save_shot=False, phash=False):
        if not self.run_html(html_file): return
        for mut in muts: self.exec_script(mut)

        # TODO: stop all animation and save all stateus
        self.__save_state()

        name_noext = splitext(html_file)[0]
        screenshot_name = f'{name_noext}_{self.version}_a.png' if save_shot else None
        hash_v1 = self.__screenshot_and_hash(screenshot_name, phash=phash)
        if not hash_v1: return

        self.__re_render()
        if not self.__is_same_state():
            #print ('state is different', html_file, muts)
            return
        else:
            #print ('state is same', html_file, muts)
            pass
            

        screenshot_name = f'{name_noext}_{self.version}_b.png' if save_shot else None
        hash_v2 = self.__screenshot_and_hash(screenshot_name, phash=phash)
        if not hash_v2: return

        return ImageDiff.diff_images(hash_v1, hash_v2, phash=phash)
