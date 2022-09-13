import argparse

from random import seed

from modules import Metamong

from os.path import join, dirname, basename

def main():
    parser = argparse.ArgumentParser(description='Usage')
    parser.add_argument('-i', '--input', required=True, type=str, default='', help='input directory')
    parser.add_argument('-o', '--output', required=True, type=str, help='output directory')
    parser.add_argument('-j', '--job', required=False, type=int, default=1, help='number of threads')
    parser.add_argument('-t', '--type', required=False, type=str, default='chrome', help='Browser type')
    parser.add_argument('-p', '--pre', required=True, type=int, help='Version of base Chrome (e.g., 80)')
    parser.add_argument('-n', '--new', required=True, type=int, help='version of target Chrome (e.g., 81)')
    args = parser.parse_args()

    seed(0)

    m = Metamong(args.input, args.output, args.job, args.type, args.pre, args.new)
    m.skip_minimizer()
    m.process()


if __name__ == "__main__":
    main()
