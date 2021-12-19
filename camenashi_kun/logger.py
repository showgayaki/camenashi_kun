from logging import Formatter, handlers, getLogger
from pathlib import Path


class Logger:
    def __init__(self, root_dir, name=__name__,):
        self.logger = getLogger(name)
        formatter = Formatter("[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s")

        # /[root_dir]/log/[app_name].logに出力
        root_dir = Path(root_dir).resolve()
        dir_name = root_dir.name
        log_dir = Path.joinpath(Path(root_dir).resolve(), 'log')
        # logフォルダ無かったら作成
        if not log_dir.is_dir():
            Path.mkdir(log_dir)
        filename = '{}/{}.log'.format(log_dir, dir_name)

        handler = handlers.RotatingFileHandler(
            filename=filename,
            maxBytes=1048576,
            backupCount=3,
            encoding='utf-8'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def logging(self, level, msg):
        if level == 'debug':
            self.logger.setLevel(10)
            self.logger.debug(msg)
        elif level == 'info':
            self.logger.setLevel(20)
            self.logger.info(msg)
        elif level == 'warning':
            self.logger.setLevel(30)
            self.logger.warning(msg)
        elif level == 'error':
            self.logger.setLevel(40)
            self.logger.error(msg)
        elif level == 'critical':
            self.logger.setLevel(50)
            self.logger.critical(msg)
