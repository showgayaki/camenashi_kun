import os
from dotenv import load_dotenv
from pathlib import Path


class Config:
    def __init__(self, root_dir):
        self.root_dir = root_dir

    def fetch_config(self):
        dotenv_path = Path(self.root_dir).resolve().joinpath('.env')
        load_dotenv(dotenv_path)
        conf = {
            'app_name': 'Camenashi Kun',
            'mail_info': {
                'smtp_server': os.environ.get('SMTP_SERVER'),
                'smtp_port': os.environ.get('SMTP_PORT'),
                'smtp_user': os.environ.get('SMTP_USER'),
                'smtp_pass': os.environ.get('SMTP_PASS'),
                'mail_to': os.environ.get('MAIL_TO'),
                'mail_cc': os.environ.get('MAIL_CC')
            },
            'camera_info': {
                'camera_ip': os.environ.get('CAMERA_IP'),
                'camera_user': os.environ.get('CAMERA_USER'),
                'camera_pass': os.environ.get('CAMERA_PASS')
            },
            'notice_threshold': int(os.environ.get('NOTICE_THRESHOLD')),
            'detect_label': set(os.environ.get('DETECT_LABEL').split(',')),
            # 'detect_list': set(os.environ.get('DETECT_LIST').split(','))
            'capture_interval': int(os.environ.get('CAPTURE_INTERVAL')),
            'pause_seconds': int(os.environ.get('PAUSE_SECONDS')),
        }
        return conf
