from helper import FileManager
from random import randrange, choice, sample

class MetaMut:
    def __init__(self):
        self.__tags = []
        for tag in FileManager.read_file('../data/html_tags'):
            self.__tags.append(tag[1:-2])

        self.mut_func = []

        low_weight_list = [
             self.move_node,
             self.tag_change,# 99 / 100
        ]

        high_weight_list = [
             self.del_node, # 100 / 100
             self.del_attribute, # 99 / 100
             self.del_css, # 98 / 100
             self.meta_scroll,
             self.meta_wscroll,
            ]

        self.mut_func.extend(low_weight_list * 1)
        self.mut_func.extend(high_weight_list * 3)

        self.min_num = 1
        self.max_num = 5

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
        self.attributes = dic['attributes']
        self.css_length = dic['css_length']

    # METAMORPHIC

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


    def tag_change(self):
        id_ = choice(self.ids)
        tag = choice(self.__tags)
        return f"window.Mut = new window.TagChange('{id_}', '{tag}');"

    def add_node(self, ids, position, html):
        pass

    def del_node(self):
        id_ = choice(self.ids)
        return f"window.Mut = new window.DelNode('{id_}');"

    def move_node(self):
        id1, id2 = sample(self.ids, 2)
        return f"window.Mut = new window.MoveNode('{id1}', '{id2}');"

    # def add_attribute(self, ids):
    #     pass

    def del_attribute(self):
        id_ = choice(self.ids)
        attrn = choice(self.attributes[id_])
        return f"window.Mut = new window.DelAttribute('{id_}', '{attrn}');"

    # def add_css(self, css):
    #     pass

    def del_css(self):
        target_index = randrange(self.css_length)
        return f"window.Mut = new window.DelCSS({target_index});"

    # def del_css_property(self):
    #     pass

    def meta_scroll(self):
        ret = []
        id_ = choice(self.ids)
        left = randrange(1000)
        top = randrange(1000)
        
        ret.append(f"window.Mut = new MetaScroll('{id_}', {left}, {top});")
        ret.append(f"window.Mut.restore();")

        return ret

    def meta_wscroll(self):
        ret = []
        left = randrange(1000)
        top = randrange(1000)
        
        ret.append(f"window.Mut = new MetaWScroll({left}, {top});")
        ret.append(f"window.Mut.restore();")

        return ret
