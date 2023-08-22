import os
import sys
import bisect
from pyvirtualdisplay import Display
from utils.driver import Browser
from utils.helper import VersionManager
from utils.helper import FileManager
from utils.helper import ImageDiff

import json
import time

def test(html_dir):
    if not os.path.isdir(html_dir): return

    con_file = os.path.join(html_dir, 'config.json')
    poc_file = os.path.join(html_dir, 'poc.html')
    exp_file = os.path.join(html_dir, 'expected.html')
    js_file = os.path.join(html_dir, 'poc.js')

    with open(con_file) as f:
        json_object = json.load(f)
        browser_type = json_object["type"]
        ver = json_object["fixed_ver"]

    js = FileManager.read_file(js_file)
    muts = js.split('\n')

    vm = VersionManager(browser_type)
    if browser_type == 'chrome':
        index = bisect.bisect_left(vm.revlist, ver)
        version = vm.revlist[index - 1]
    else:
        if ver:
            version = ver - 1
        else:
            version = json_object["target_ver"]

    disp = Display(size=(1600, 1200))
    disp.start()
    use_popup = True
    if "nopopup" in json_object:
        use_popup = False

    is_bug = False
    for _ in range(3):
        b = Browser(browser_type, version, popup=use_popup)
        b.setup_browser()

        b.run_html_for_actual(poc_file, muts)

        poc_png = poc_file.replace('.html', '.png')
        b.get_screenshot(poc_png)
        poc_hash, _ = ImageDiff.get_phash(poc_png)
        b.kill_browser()

        b = Browser(browser_type, version, popup=use_popup)
        b.setup_browser()
        #b.run_html(exp_file)
        b.run_html_for_expect(poc_file, muts, exp_file)
        exp_png = exp_file.replace('.html', '.png')
        b.get_screenshot(exp_png)
        exp_hash, _ = ImageDiff.get_phash(exp_png)

        if ImageDiff.diff_images(poc_hash, exp_hash, phash=True):
            print ('Oracle detects the bug, poc:', poc_file)
            is_bug = True
            break

        b.kill_browser()

    if not is_bug:
        print ('Oracle fails..., poc:', poc_file)

    disp.stop()
    return is_bug


if __name__ == "__main__":
    url = sys.argv[1]
    num = 0
    bug = 0
    for directory in sorted(os.listdir(url)):
        path = os.path.join(url, directory)
        if not os.path.isdir(path): continue
        num += 1
        if test(path): 
            bug += 1
    print (f'bug: {bug}, num: {num}')
