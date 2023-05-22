from random import randrange, choice, sample
from utils.helper import FileManager

from old_domato.generator import gen_html, gen_attribute, gen_css
from old_domato.generator import setup_for_html_generation

class MetaMut:
    def __init__(self):
        self.__tags = []
        for tag in FileManager.read_file('../data/html_tags').split('\n'):
            self.__tags.append(tag)

        self.__tags.remove('')

        self.mut_func = [
            # DOM
            self.add_node,
            self.del_node,

            self.add_attribute,
            self.del_attribute,

            self.focus,
            self.scroll,
            self.resize,

            # CSS
            self.add_css,
            self.del_css,
        ]

        self.min_num = 1
        self.max_num = 1 # 8


        self.hg, self.cg = setup_for_html_generation()

    def save_state(self):
        return 'window.SC = new window.StateChecker();'

    def re_render(self):
        return 'window.SC.write_document();'

    def get_page(self):
        return 'return window.SC.get_page();'

    def is_same_state(self):
        return 'return window.SC.is_same_state();'

    def load_state(self, dic):
        self.ids = dic['ids']
        self.full_ids = self.ids.copy()
        self.full_ids.append("head")
        self.full_ids.append("body")
        self.attributes = dic['attributes']
        self.css_length = dic['css_length']

    def generate(self):
        muts = []
        num_of_func = randrange(self.min_num, self.max_num + 1)
        for _ in range(num_of_func):
            api = choice(self.mut_func)()
            if isinstance(api, str):
                muts.append(api)
            else:
                muts.extend(api)

        return muts

    def add_node(self):
        id_ = choice(self.ids)
        pos = choice(['beforebegin', 'afterbegin', 'beforeend', 'afterend']) 
        html = gen_html(self.hg)
        return f"window.Mut = new window.AddNode('{id_}', '{pos}', `{html}`);" 

    def del_node(self):
        id_ = choice(self.ids)
        return f"window.Mut = new window.DelNode('{id_}');"

    def add_attribute(self):
        id_ = choice(self.ids)
        attr = gen_attribute(self.hg)
        attrn, attrv = attr.split("=")
        return f"window.Mut = new window.AddAttribute('{id_}', '{attrn}', {attrv});"

    def del_attribute(self):
        id_ = choice(self.ids)
        if not self.attributes[id_]:
            return ""
        attrn = choice(self.attributes[id_])
        return f"window.Mut = new window.DelAttribute('{id_}', '{attrn}');"

    def add_css(self):
        id_ = choice(self.ids)
        decl = "{ " + gen_css(self.cg) + "; }"
        rule = f"#{id_} {decl}"
        return f"window.Mut = new window.AddCSS(\"{rule}\")"

    def del_css(self):
        target_index = randrange(self.css_length)
        return f"window.Mut = new window.DelCSS({target_index});"

    def focus(self):
        id_ = choice(self.full_ids)
        return f"focusing('{id_}')"

    def scroll(self):
        id_ = choice(self.full_ids)
        l = randrange(1000)
        t = randrange(1000)
        return f"scrolling('{id_}', {l}, {t})"

    def resize(self):
        w = randrange(100, 1000)
        h = randrange(100, 1000)
        return f"resizing({w}, {h})"
