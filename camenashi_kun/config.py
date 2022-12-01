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
            'line_info': {
                'api_url': os.environ.get('LINE_API_URL'),
                'access_token': os.environ.get('LINE_ACCESS_TOKEN'),
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
            'black_screen_seconds': int(os.environ.get('BLACK_SCREEN_SECONDS')),
        }
        return conf
