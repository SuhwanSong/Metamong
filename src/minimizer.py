import os
import re

from bs4 import BeautifulSoup
from typing import Optional, Tuple
from threading import Thread

from shutil import copyfile
from os.path import basename, join, dirname

from fuzzer import Fuzzer
from utils.helper import IOQueue
from utils.helper import FileManager

class Minimizer(Thread):
    def __init__(self, helper: IOQueue, browser_type: str) -> None:

        self.__fuzzer = Fuzzer(helper, browser_type)

        self.__min_html = None
        self.__html_file = None
        self.__temp_file = None
        self.__trim_file = None
        self.__js_file = None

    def __remove_temp_files(self):
        os.remove(self.__temp_file)
        os.remove(self.__trim_file)


    def __test_html(self, html_file: str, muts: list):
        return self.__fuzzer.test_html(html_file, muts)

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
        return self.__test_html(html_file, self.__muts)

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

                if self.__test_html(self.__trim_file, self.__muts):
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
        br = self.__fuzzer.get_newer_browser()
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
            if self.__test_html(self.__trim_file, self.__muts):
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
                    if self.__test_html(self.__trim_file, self.__muts):
                        self.__min_html = text
                        FileManager.write_file(self.__temp_file, self.__min_html)

    def __minimize_inner_element(self):
        br = self.__fuzzer.get_newer_browser()
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
            if self.__test_html(self.__trim_file, self.__muts):
                self.__min_html = text
                FileManager.write_file(self.__temp_file, self.__min_html)

    def __minimize_text(self):
        br = self.__fuzzer.get_newer_browser()
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
            if self.__test_html(self.__trim_file, self.__muts):
                self.__min_html = text
                FileManager.write_file(self.__temp_file, self.__min_html)

    def __minimize_js(self):
        muts = self.__muts.copy()
        for i in reversed(range(len(muts))):
            removed = muts.pop(i)
            if self.__test_html(self.__temp_file, muts):
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
  
                if self.__test_html(self.__temp_file, self.__muts):
                    orig_html_file = os.path.splitext(html_file)[0] + '-orig.html'
                    os.rename(html_file, orig_html_file) 
                    copyfile(self.__temp_file, html_file)
                    hpr.update_postq(vers, html_file, self.__muts)

            self.__remove_temp_files()

        self.stop_browsers()
