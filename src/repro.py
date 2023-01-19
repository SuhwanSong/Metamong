import os
import sys
import bisect
from pyvirtualdisplay import Display
from utils.driver import Browser
from utils.helper import VersionManager
from utils.helper import FileManager
from utils.helper import ImageDiff

import time

def test(html_dir):
    if not os.path.isdir(html_dir): return 
    ver_file = os.path.join(html_dir, 'fixed_ver.txt')
    poc_file = os.path.join(html_dir, 'poc.html')
    exp_file = os.path.join(html_dir, 'expected.html')
    js_file = os.path.join(html_dir, 'poc.js')

    js = FileManager.read_file(js_file)
    muts = js.split('\n')
    ver = FileManager.read_file(ver_file)

    vm = VersionManager('chrome')
    index = bisect.bisect_left(vm.revlist, int(ver))

    #disp = Display(size=(1600, 1200))
    #disp.start()
    use_popup = True

    b = Browser('chrome', vm.revlist[index - 1], popup=use_popup)
    b.setup_browser()

    b.run_html_for_actual(poc_file, muts) 

    poc_png = poc_file.replace('.html', '.png')
    b.get_screenshot(poc_png)
    poc_hash = ImageDiff.get_phash(poc_png)
    b.kill_browser()
    
    b = Browser('chrome', vm.revlist[index - 1], popup=use_popup)
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
