import sys
import time, psutil
from pathlib import Path

from selenium import webdriver
from collections import defaultdict

from os import environ, remove
from os.path import dirname, join, abspath, splitext, exists

from utils.helper import ImageDiff
from utils.helper import FileManager
from utils.chrome_binary import ChromeBinary
from utils.firefox_binary import FirefoxBinary


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
    def __init__(self, browser_type: str, commit_version: int, flags: str = '', popup: bool = False, vid_: str = '') -> None:
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

        self.__popup = popup
        self.__vid = vid_

    def __set_viewport_size(self):
        window_size = self.browser.execute_script("""
        return [window.outerWidth - window.innerWidth + arguments[0],
          window.outerHeight - window.innerHeight + arguments[1]];
        """, self.__width, self.__height)

        if window_size is None: return
        elif window_size[0] == 800 and window_size[1] == 600: return
        else: self.browser.set_window_size(*window_size)

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

    def setup_browser(self):
        self.__num_of_run = 0
        self.browser = None
        parent_dir = FileManager.get_parent_dir(__file__)
        browser_dir = join(dirname(parent_dir), self.__browser_type)
        if not exists(browser_dir):
            Path(browser_dir).mkdir(parents=True, exist_ok=True)


        for _ in range(5):
            try:
                if self.__browser_type == 'chrome':
                    options = [
#                            '--headless',
                            '--disable-seccomp-sandbox',
                            '--disable-logging',
                            '--disable-gpu',
                            f'--window-size={self.__width},{self.__height}',
                            ]
                    options.extend(self.flags)
                    if self.__vid: options.append(f'--display={self.__vid}')
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
#                            '--headless',
                            '--disable-gpu',
#                            f'--width={self.__width}',
#                            f'--height={self.__height}',
                            ]
                    if self.__vid: options.append(f'--display={self.__vid}')
                    option = webdriver.firefox.options.Options()
                    fb = FirefoxBinary()
                    fb.ensure_firefox_binaries(browser_dir, self.version)
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
                print (e, 'here')
                time.sleep(0.2)
                continue

        # System crashes if fails to start browser.
        if self.browser is None:
            print (f"Browser {self.version} fails to start..")
            sys.exit(1)

        TIMEOUT = 10
        self.browser.set_script_timeout(TIMEOUT)
        self.browser.set_page_load_timeout(TIMEOUT)
        self.browser.implicitly_wait(TIMEOUT)

        setup_complete = False
        for _ in range(5):
            try:
                if self.__popup:
                    self.exec_script(f'window.open("", "", {self.__width}, {self.__height})')
                    self.browser.switch_to.window(self.browser.window_handles[1])
                platform = sys.platform
                platform_funcs = {'linux': self.__set_viewport_size,
                                  'darwin': self.__adjust_viewport_size, }
                platform_funcs[platform]()
                setup_complete = True
                break
            except Exception as e:
                print (e)
                continue

        return setup_complete

    def kill_browser(self):
        if self.browser and self.browser.session_id:
            try:
                self.browser.close()
                self.browser.quit()
            except:
                return False

        return True

    def kill_browser_by_pid(self):
        if not self.browser: return False
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
        try:
            if self.__popup: self.__set_viewport_size()
            self.browser.get('file://' + abspath(html_file))
            self.__num_of_run += 1
            return True
        except Exception as e:
            return False

    def run_html_for_actual(self, html_file: str, muts: list):
        if self.__num_of_run == 1000:
            self.kill_browser()
            self.setup_browser()

        #text = FileManager.read_file(html_file)
        #self.exec_script(f'document.write(`{text}`);')
        if not self.run_html(html_file): return False
        for mut in muts:
            self.exec_script(mut)
            time.sleep(0.5)
        self.__num_of_run += 1
        #self.exec_script(f'document.close();')
        return True

    def run_html_for_expect(self, html_file: str, muts: list, name=''):
        if self.__num_of_run == 1000:
            self.kill_browser()
            self.setup_browser()

        if self.__popup: 
            try: self.__set_viewport_size()
            except Exception as e: return False
        text = FileManager.read_file(html_file)
        js = '\n;'.join(muts)
        text += '\n' + f'<script>{js}</script>'
        if name:
            FileManager.write_file(name, text)
            self.run_html(name)
        else:
            self.exec_script(f'document.write(`{text}`);')
            self.exec_script(f'document.close();')
        self.__num_of_run += 1
        return True

    def get_screenshot(self, name: str = ''):
        for attempt in range(5):
            if attempt == 4:
                self.kill_browser()
                self.setup_browser()
            try:
                png = self.browser.get_screenshot_as_png()
                if name: ImageDiff.save_image(name, png)
                return png
            except Exception as e:
                continue

        return None

    def get_dom_tree_info(self):
        return self.exec_script(GET_ATTRNAMES)

    def analyze_html(self, html_file):
        dic = {}
        if not self.run_html(html_file): return 

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

    def __get_all_state(self):
        state = {}
        try:
            #state["dom"] = self.exec_script("return get_dom_tree();")
            #state["css"] = self.exec_script("return get_css_rules();")
            state["focus"] = self.exec_script("return get_focus_node();")
            state["scroll"] = self.exec_script("return get_scroll_position();")
            state["animation"] = self.exec_script("return get_animations();")
            return state
        except Exception as e:
            print (e)
            return {}

    def __state_compare(self, s1, s2):
        for key in s1:
            if s1[key] != s2[key]:
                return False
        return True

    def metamor_test(self, html_file, muts, save_shot=False, phash=False):
        if self.exec_script("return document.location.href") is None:
            self.kill_browser_by_pid()
            self.setup_browser()

        if not self.run_html_for_actual(html_file, muts): return

        name_noext = splitext(html_file)[0]
        screenshot_name = f'{name_noext}_{self.version}_a.png' if save_shot else None
        hash_v1 = self.__screenshot_and_hash(screenshot_name, phash=phash)
        if not hash_v1: return

        # save state
        actual_state = self.__get_all_state()
        if not actual_state: return

        exp_file = html_file.replace('.html', '_expected.html')
        if not self.run_html_for_expect(html_file, muts, exp_file): return 

        screenshot_name = f'{name_noext}_{self.version}_b.png' if save_shot else None
        hash_v2 = self.__screenshot_and_hash(screenshot_name, phash=phash)
        if not hash_v2: return

        expected_state = self.__get_all_state()
        if not expected_state: return

        if not self.__state_compare(actual_state, expected_state): return

        # size is different
        if hash_v1[1] != hash_v2[1]: return

        return ImageDiff.diff_images(hash_v1[0], hash_v2[0], phash=phash)
