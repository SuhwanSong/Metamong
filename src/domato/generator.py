#   Domato - main generator script
#   --------------------------------------
#
#   Written and maintained by Ivan Fratric <ifratric@google.com>
#
#   Copyright 2017 Google Inc. All Rights Reserved.
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from __future__ import print_function
import os
import re
import random
import argparse

from grammar import Grammar
from svg_tags import _SVG_TYPES
from html_tags import _HTML_TYPES
from mathml_tags import _MATHML_TYPES

from multiprocessing import Process


_N_ADDITIONAL_HTMLVARS = 5

def generate_html_elements(ctx, n):
    for i in range(n):
        tag = random.choice(list(_HTML_TYPES))
        tagtype = _HTML_TYPES[tag]
        ctx['htmlvarctr'] += 1
        varname = 'htmlvar%05d' % ctx['htmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': tagtype})
        ctx['htmlvargen'] += '/* newvar{' + varname + ':' + tagtype + '} */ var ' + varname + ' = document.createElement(\"' + tag + '\"); //' + tagtype + '\n'


def add_html_ids(matchobj, ctx):
    tagname = matchobj.group(0)[1:-1]
    if tagname in _HTML_TYPES:
        ctx['htmlvarctr'] += 1
        varname = 'htmlvar%05d' % ctx['htmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _HTML_TYPES[tagname]})
        ctx['htmlvargen'] += '/* newvar{' + varname + ':' + _HTML_TYPES[tagname] + '} */ var ' + varname + ' = document.getElementById(\"' + varname + '\"); //' + _HTML_TYPES[tagname] + '\n'
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    elif tagname in _SVG_TYPES:
        ctx['svgvarctr'] += 1
        varname = 'svgvar%05d' % ctx['svgvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _SVG_TYPES[tagname]})
        ctx['htmlvargen'] += '/* newvar{' + varname + ':' + _SVG_TYPES[tagname] + '} */ var ' + varname + ' = document.getElementById(\"' + varname + '\"); //' + _SVG_TYPES[tagname] + '\n'
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    elif tagname in _MATHML_TYPES:
        ctx['mathmlvarctr'] += 1
        varname = 'mathmlvar%05d' % ctx['mathmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _MATHML_TYPES[tagname]})
        ctx['htmlvargen'] += '/* newvar{' + varname + ':' + _MATHML_TYPES[tagname] + '} */ var ' + varname + ' = document.getElementById(\"' + varname + '\"); //' + _MATHML_TYPES[tagname] + '\n'
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    else:
        return matchobj.group(0)



def check_grammar(grammar):
    """Checks if grammar has errors and if so outputs them.
    Args:
      grammar: The grammar to check.
    """

    for rule in grammar._all_rules:
        for part in rule['parts']:
            if part['type'] == 'text':
                continue
            tagname = part['tagname']
            # print tagname
            if tagname not in grammar._creators:
                print('No creators for type ' + tagname)


def generate_new_sample(template, htmlgrammar, cssgrammar):
    """Parses grammar rules from string.
    Args:
      template: A template string.
      htmlgrammar: Grammar for generating HTML code.
      cssgrammar: Grammar for generating CSS code.
    Returns:
      A string containing sample data.
    """

    result = template

    css = cssgrammar.generate_symbol('rules')
    html = htmlgrammar.generate_symbol('bodyelements')

    htmlctx = {
        'htmlvars': [],
        'htmlvarctr': 0,
        'svgvarctr': 0,
        'mathmlvarctr': 0,
        'htmlvargen': ''
    }
    html = re.sub(
        r'<[a-zA-Z0-9_-]+ ',
        lambda match: add_html_ids(match, htmlctx),
        html
    )
    generate_html_elements(htmlctx, _N_ADDITIONAL_HTMLVARS)

    result = result.replace('<cssfuzzer>', css)
    result = result.replace('<htmlfuzzer>', html)
    return result

def generate_samples(template, outfiles):
    """Generates a set of samples and writes them to the output files.
    Args:
      grammar_dir: directory to load grammar files from.
      outfiles: A list of output filenames.
    """

    grammar_dir = os.path.join(os.path.dirname(__file__), 'rules')
    htmlgrammar = Grammar()

    err = htmlgrammar.parse_from_file(os.path.join(grammar_dir, 'html.txt'))
    # CheckGrammar(htmlgrammar)
    if err > 0:
        print('There were errors parsing html grammar')
        return

    cssgrammar = Grammar()
    err = cssgrammar.parse_from_file(os.path.join(grammar_dir ,'css.txt'))
    # CheckGrammar(cssgrammar)
    if err > 0:
        print('There were errors parsing css grammar')
        return


    # Add it as import
    htmlgrammar.add_import('cssgrammar', cssgrammar)

    for outfile in outfiles:
        result = generate_new_sample(template, htmlgrammar, cssgrammar)
        if result is not None:
            print('Writing a sample to ' + outfile)
            try:
                with open(outfile, 'w') as f:
                    f.write(result)
            except IOError:
                print('Error writing to output')

def get_argument_parser():
    
    parser = argparse.ArgumentParser(description="DOMATO (A DOM FUZZER)")
    
    parser.add_argument("-f", "--file", 
    help="File name which is to be generated in the same directory")

    parser.add_argument('-o', '--output_dir', type=str,
                    help='The output directory to put the generated files in')

    parser.add_argument('-n', '--no_of_files', type=int,
                    help='number of files to be generated')

    return parser

def main(index):

    fuzzer_dir = os.path.dirname(__file__)

    with open(os.path.join(fuzzer_dir, "template.html"), "r") as f:
        template = f.read()

    parser = get_argument_parser()
    
    args = parser.parse_args()

    if args.file:
        generate_samples(template, [args.file])

    elif args.output_dir:
        if not args.no_of_files:
            print("Please use switch -n to specify the number of files")
        else:
            print('Running on ClusterFuzz')
            out_dir = args.output_dir
            nsamples = args.no_of_files
            print('Output directory: ' + out_dir)
            print('Number of samples: ' + str(nsamples))

            if not os.path.exists(out_dir):
                os.mkdir(out_dir)

            outfiles = []
            for i in range(nsamples):
                outfiles.append(os.path.join(out_dir, f'{index}-{str(i).zfill(7)}.html'))
            
            generate_samples(template, outfiles)
                

    else:
        parser.print_help()


if __name__ == '__main__':
    ps = []
    for i in range(os.cpu_count()):
        p = Process(target=main, args=(i,))
        p.start()

        ps.append(p)
    for p in ps:
        p.join()
