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

    #disp = Display(size=(1600, 1200))
    #disp.start()
    use_popup = True
    if "popup" in json_object:
        use_popup = json_object["popup"]

    b = Browser(browser_type, version, popup=use_popup)
    b.setup_browser()

    b.run_html_for_actual(poc_file, muts) 
    time.sleep(10)

    poc_png = poc_file.replace('.html', '.png')
    b.get_screenshot(poc_png)
    poc_hash = ImageDiff.get_phash(poc_png)
    b.kill_browser()
    
    b = Browser(browser_type, version, popup=use_popup)
    b.setup_browser()
    #b.run_html(exp_file) 
    b.run_html_for_expect(poc_file, muts, exp_file)
    exp_png = exp_file.replace('.html', '.png')
    b.get_screenshot(exp_png)
    exp_hash = ImageDiff.get_phash(exp_png)

    if ImageDiff.diff_images(poc_hash, exp_hash, phash=True):
        print ('Oracle detects the bug')
    else: 
        print ('Oracle fails...')

    b.kill_browser()
    #disp.stop()

test(sys.argv[1])
