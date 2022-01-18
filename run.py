import argparse
from camenashi_kun.core import main


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-view', default=False, action='store_true', help='hide stream')
    opt = parser.parse_args()
    return opt


if __name__ == '__main__':
    opt = parse_opt()
    main(**vars(opt))
