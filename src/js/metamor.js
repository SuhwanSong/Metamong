function get_elements() {
    return document.body.querySelectorAll('*');
}

function get_all_ids() {
    let allIds = [];
    let allElements = get_elements();

    for (let i = 0; i < allElements.length; i++) {
        let name = allElements[i].id.toString();
        if (name && allIds.indexOf(name) === -1)
            allIds.push(name);
    }
    return allIds;
}

function get_all_attributes() {
    let attr = {};
    let allElements = get_elements();
    for (let i = 0; i < allElements.length; i++) {
        let ele = allElements[i];
        attr[ele.id] = [];
        for (let j = 0, l = ele.attributes.length; j < l; j++) {
            const name = ele.attributes.item(j).nodeName;
            if (name !== 'id') {
                attr[ele.id].push(name);
            }
        }
    }
    return attr;
}

function get_css_length() {
    let style = document.styleSheets[0];
    if (!style)
        return 0;
    return style.cssRules.length;
}

function get_attribute() {
    let attr = [];
    let allElements = get_elements();
    for (let i = 0; i < allElements.length; i++) {
        let ele = allElements[i];
        let tmp = [];
        for (let j = 0, l = ele.attributes.length; j < l; j++) {
            const name = ele.attributes.item(j).nodeName;
            if (name != 'id') {
                tmp.push(name);
            }
        }
        attr.push(tmp);
    }
    return attr;
}

function get_dom_tree() {
    return document.body.outerHTML;
}

function get_css_rules() {
    if (!document.styleSheets) return '';

    let styleSheet = document.styleSheets[0];
    if (!styleSheet || !styleSheet.cssRules) return '';

    let css_r = [];
    let css_rules = styleSheet.cssRules;

    for (let i = 0; i < css_rules.length; i++) {
        css_r.push(css_rules[i].cssText);
    }
    return css_r.join('\n');
}


function get_focus_node() {
    return document.activeElement.id;
}

function get_scroll_positions() {
    let positions = [`${window.scrollX},${window.scrollY}`];

    let allElements = get_elements();
    for (let i = 0; i < allElements.length; i++) {
        let ele = allElements[i];
        if (ele.scrollTop && ele.scrollLeft)
          positions.push(`${ele.scrollTop},${ele.scrollLeft}`);
    }
    return positions.join('\n');
}

function get_animations() {
    return document.getAnimations().length;
}

/* rendering checker */
window.StateChecker = class StateChecker {
    constructor() {
        this.cancel_transitions();
        this.cancel_animations();

        this.dom_tree = this.get_dom_tree();
        //this.css_rule = this.get_css_rules();
        this.focus_node = this.get_focus_node();
        this.scroll_positions = this.get_scroll_positions(this.dom_tree);
        this.animations = this.get_animations();

        this.page_html = this.get_page();
    }

    get_dom_tree() {
        return document.body.cloneNode(true);
    }

    get_css_rules() {
        if (!document.styleSheets) return '';

        let styleSheet = document.styleSheets[0];
        if (!styleSheet || !styleSheet.cssRules) return '';

        let css_r = [];
        let css_rules = styleSheet.cssRules;

        for (let i = 0; i < css_rules.length; i++) {
            css_r.push(css_rules[i].cssText);
        }
        return css_r.join('\n');
    }
    
    get_focus_node() {
        return document.activeElement.cloneNode(true);
    }

    get_scroll_positions(allElements) {
        let positions = [[window.scrollX, window.scrollY]];
        for (let i = 0; i < allElements.length; i++) {
            let ele = allElements[i];
            positions.push([ele.scrollTop, ele.scrollLeft]);
        }
        return positions;
    }

    get_animations() {
//        let anis = document.getAnimations();
//        for (let i = 0; i < anis.length; i++) {
//            anis[i].pause();
//        }
//        let times = {};
//        for (let i = 0; i < anis.length; i++) {
//            let ani = anis[i];
//            let aniName = ani.animationName;
//            if (!(aniName in times)) {
//                times[aniName] = {};
//            }
//            times[aniName][ani.effect.target.id] = ani.currentTime;
//        }
//        return times;
        return document.getAnimations().length;
    }

    cancel_animations() {
        let anis = document.getAnimations();
        for (let i = 0; i < anis.length; i++) {
            let ani = anis[i];
            if (Object.prototype.toString.call(ani) === "[object CSSAnimation]") {
                ani.cancel();        
            }
        }
    }

    cancel_transitions() {
        let anis = document.getAnimations();
        for (let i = 0; i < anis.length; i++) {
            let ani = anis[i];
            if (Object.prototype.toString.call(ani) === "[object CSSTransition]") {
                ani.cancel();        
            }
        }
    }

    fit_animations() {
        let js = `<script id="fit">
        let foc = document.getElementById(window.SC.focus_node.id);
        if (foc) {
            foc.focus();
        }
        let ani_dict = {};
        let anis = document.getAnimations();
        for (let i = 0; i < anis.length; i++) {
            let ani = anis[i];
            ani.cancel();
        }
        </script>`
        return js;
    }

    compare_nodes(a, b) {
        if (a.querySelectorAll('*').length !== b.querySelectorAll('*').length) return false;
        if (a.outerHTML !== b.outerHTML) return false;
        return true;
    }

    is_dom_same() {
        let node = this.get_dom_tree();
        let fit = node.querySelector('#fit');
        if (fit) { fit.remove(); }
        return this.compare_nodes(this.dom_tree, node);
    }

    is_css_same() {
        return this.css_rule === this.get_css_rules();
    }

    is_focus_same() {
        let node = this.get_focus_node();
        let fit = node.querySelector('#fit');
        if (fit) { fit.remove(); }
        return this.compare_nodes(this.focus_node, node);
    }

    is_scroll_position_same() {
        let node = this.get_dom_tree();
        let fit = node.querySelector('#fit');
        if (fit) { fit.remove(); }

        let a = this.scroll_positions;
        let b = this.get_scroll_positions(node);

        if (a.length !== b.length) return false;
        for (let i = 0; i < a.length; i++) {
            if (a[i][0] !== b[i][0] || a[i][1] !== b[i][1]) return false;
        }

        return true;
    }

    is_animation_same() {
//        let anis = this.get_animations();
//        for (var key in this.animations) {
//            if (!(key in anis) || anis[key] != this.animations[key]) return false;
//        }
//        for (var key in anis) {
//            if (!(key in this.animations)) {
//                return false;
//            }
//        }
//        return true;
        return this.animations == 0 && this.get_animations() == 0;
    }

    is_same_state() {
        if (
//            !this.is_css_same() ||
            !this.is_dom_same() ||
            !this.is_focus_same() || 
            !this.is_scroll_position_same() || 
            !this.is_animation_same()
           )  
            return false;
        else
            return true;
    }

    get_page () {
        let outer = document.body.outerHTML;
        let css = "<!DOCTYPE html>\n<html><head><style>";
        if (document.styleSheets) {
            let styleSheet = document.styleSheets[0];
            let css_r = [];
            if (styleSheet && styleSheet.cssRules) {
                let css_rules = styleSheet.cssRules;
                for (let i = 0; i < css_rules.length; i++) {
                    let rr = css_rules[i];
                    css_r.push(rr.cssText);
                }
            }
            if (css_r.length) {
                css += css_r.join('\n');
            }
        }
        return css + "</style><script src='/tmp/metamor.js'></script></head>" + outer + this.fit_animations() + "</html>";
    }

    write_document() {
        document.open();
        document.write(this.page_html);
        document.close();
    }
}

window.Diff = class Diff {
    consturctor() {
        this.lose_focus();
        this.orig_style = this.get_computed_style();
        this.orig_layout = this.get_layout();
    }

    get_computed_style() {
        let result = [];
        const eles = document.body.querySelectorAll('*');
        for (let i = 0; i < eles.length; i++) {
            let dict = {};
            let rect = getComputedStyle(eles[i]);
            for (let j = 0; j < rect.length; j++) {
                let key = rect[j];
                dict[key] = rect[key];
            }
            result.push(dict);
        }
        return result;
    }

    get_layout() {
        let result = [];
        const eles = document.body.querySelectorAll('*');
        for (let i = 0; i < eles.length; i++) {
            let dict = {};
            let rect = eles[i].getBoundingClientRect();;
            for (var key in rect) {
                if(typeof rect[key] !== 'function') {
                    dict[key] = rect[key];
                }
            }
            result.push(dict);
        }
        return result;
    }
}


window.TagChange = class TagChange {
    constructor (id, new_tag) {
        let orl = document.getElementById(id);
        this.mutable = true;
        if (!orl) {
            this.mutable = false;
        } else {
            this.rep = document.createElement(new_tag);
            for(let i = 0, l = orl.attributes.length; i < l; ++i){
                let nName  = orl.attributes.item(i).nodeName;
                let nValue = orl.attributes.item(i).nodeValue;
                this.rep.setAttribute(nName, nValue);
            }

            this.rep.innerHTML = orl.innerHTML;
            orl.parentElement.replaceChild(this.rep, orl);
            //this.par = rep.parentNode;
            this.orl = orl;
        }
    }

    restore () {
        if (this.mutable) {
            this.rep.parentElement.replaceChild(this.orl, this.rep);
            //this.par.replaceChild(this.orl, this.rep);
        }
    }
}

window.AddNode = class AddNode {
    constructor (id, pos, html) {
        let node = document.getElementById(id);
        if (node) { 
            this.new_node = this.html_to_element(html);
            node.insertAdjacentElement(pos, this.new_node);
        }
    }

    html_to_element(html) {
        let template = document.createElement('template');
        html = html.trim();
        template.innerHTML = html;
        return template.content.firstChild;
    }
}

window.DelNode = class DelNode {
    constructor (id) {
        let node = document.getElementById(id);
        this.mutable = true;
        if (!node) {
            this.mutable = false;
        } else {
            this.par = node.parentNode;
            this.par_inner = this.par.innerHTML;
            node.remove();
        }
    }

    restore () {
        if (this.mutable) {
            this.par.innerHTML = this.par_inner;
        }
    }
}

window.MoveNode = class MoveNode {
    constructor (id1, id2) {
        this.mutable = true;
        let node1 = document.getElementById(id1);
        let node2 = document.getElementById(id2);
        if (!node1 || !node2 || 
            node1.isSameNode(node2) ||
            node1.contains(node2) ||
            node2.contains(node1)
           ) {
            this.mutable = false;
        } else {
            this.node1 = node1;
            this.par = node1.parentNode;
            this.par_inner = this.par.innerHTML;
            node2.appendChild(node1);
        }
    }

    restore() {
        if (this.mutable) {
            this.node1.remove();
            this.par.innerHTML = this.par_inner;
        }
    }
}

window.AddAttribute = class AddAttribute {
    constructor (id, attrn, attrv) {
        let node = document.getElementById(id);
        this.mutable = true;
        if (!node) {
            this.mutable = false;
        } else {
            this.attrn = attrn;
            this.attrv = node.getAttribute(attrn);
            node.setAttribute(attrn, attrv);
            this.node = node;
        }
    }

    restore () {
        if (this.mutable) {
            if (this.attrv) {
                this.node.setAttribute(this.attrn, this.attrv);
            } else {
                this.node.removeAttribute(this.attrn);
            }
        }
    }
}

window.DelAttribute = class DelAttribute {
    constructor (id, attr_name) {
        let node = document.getElementById(id);
        this.mutable = true;
        if (!node) {
            this.mutable = false;
        } else {
            if (!node.hasAttribute(attr_name)) {
                this.mutable = false;
            } else {
                let attr_value = node.getAttribute(attr_name);
                node.removeAttribute(attr_name);
                this.node = node;
                this.attr_name = attr_name;
                this.attr_value = attr_value;
            }
        }

    }

    restore() {
        if (this.mutable) {
            this.node.setAttribute(this.attr_name, this.attr_value);
        }
    }
}

window.AddCSS = class AddCSS {
    constructor (css) {
        this.mutable = true;
        if (!document.styleSheets) {
            this.mutable = false;
        } else {
            const sheet = document.styleSheets[0];
            if (!sheet || !sheet.cssRules) {
                this.mutable = false;
            } else {
                sheet.insertRule(css, sheet.rules.length);
            }
        }
    }

    restore () {
        if (this.mutable) {
            const sheet = document.styleSheets[0];
            sheet.removeRule(sheet.rules.length - 1);
        }
    }
}

window.DelCSS = class DelCSS {
    constructor(ruleidx) {
        this.mutable = true;
        if (!document.styleSheets) {
            this.mutable = false;
        } else {
            const sheet = document.styleSheets[0];
            const num_rules = sheet.rules.length;
            if (!sheet || num_rules <= 0) {
                this.mutable = false; 
            } else {
                const pos = ruleidx % num_rules;
                this.rule_text = sheet.rules[pos].cssText;
                sheet.removeRule(pos)
                    this.rule_pos = pos;
            }
        }
    }

    restore() {
        if (this.mutable) {
            const sheet = document.styleSheets[0];
            sheet.insertRule(this.rule_text, this.rule_pos);
        }
    }
}


window.DelCSSProperty = class DelCSSProperty {
    constructor(ruleidx, propidx) {
        this.mutable = true;
        if (!document.styleSheets) {
            this.mutable = false;
        } else {
            const sheet = document.styleSheets[0];
            const num_rules = sheet.rules.length;
            if (!sheet || num_rules <= 1) {
                this.mutable = false;
            } else {
                const rule_pos = ruleidx % num_rules;
                this.rule_style = sheet.rules[rule_pos].style;
                const num_prop = this.rule_style.length;
                if (!num_prop) {
                    this.mutable = false;
                } else {
                    this.prop = this.rule_style[propidx % num_prop];
                    this.prop_val = this.rule_style[this.prop];
                    this.rule_style.removeProperty(this.prop);
                }
            }
        }
    }

    restore() {
        if (this.mutable) {
            this.rule_style.setProperty(this.prop, this.prop_val);
        }
    }
}

window.Scrolling = class Scrolling {
    constructor (id, scrollLeft, scrollTop) {
        let node = document.getElementById(id);
        this.mutable = true;
        if (!node) {
            this.mutable = false;
        } else {
            this.scrollLeft = node.scrollLeft;
            this.scrollTop = node.scrollTop;

            node.scroll(scrollLeft, scrollTop);
            this.node = node;
        }
    }

    restore () {
        if (this.mutable) {
            this.node.scroll(this.scrollLeft, this.scrollTop);
        }
    }
}

function focusing(id) {
    let node = document.getElementById(id);
    if (node) node.focus();
}

function scrolling(id, scrollLeft, scrollTop) {
    let node = document.getElementById(id);
    if (node) {
        node.scroll(scrollLeft, scrollTop);
    }
}

function resizing(width, height) {
    window.resizeTo(width, height);
}
