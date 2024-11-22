import argparse
import socket
import json
from pathlib import Path
from logging import config, getLogger

from camenashi_kun import env
from camenashi_kun.core import main


# log設定の読み込み
current_dir = Path(__file__).parent.resolve()
log_config = Path.joinpath(current_dir, current_dir.name, 'log', 'config.json')
with open(log_config) as f:
    config.dictConfig(json.load(f))

logger = getLogger(__name__)


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-view', default=False, action='store_true', help='hide stream')
    opt = parser.parse_args()
    return opt


if __name__ == '__main__':
    # アプリケーション開始ログ
    computer_name = socket.gethostname()
    logger.info(f'===== {env.APP_NAME} Started on {computer_name} =====')

    opt = parse_opt()
    main(**vars(opt))
    # アプリケーション終了ログ
    logger.info(f'===== Stop {env.APP_NAME} =====')
