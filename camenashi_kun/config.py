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
                'access_token': os.environ.get('LINE_ACCESS_TOKEN'),
                'to': os.environ.get('TO'),
            },
            'camera_info': {
                'camera_ip': os.environ.get('CAMERA_IP'),
                'camera_user': os.environ.get('CAMERA_USER'),
                'camera_pass': os.environ.get('CAMERA_PASS')
            },
            's3_bucket_name': os.environ.get('S3_BUCKET_NAME'),
            's3_expires_in': int(os.environ.get('S3_EXPIRES_IN')),
            'notice_threshold': int(os.environ.get('NOTICE_THRESHOLD')),
            'threshold_no_detected_seconds': int(os.environ.get('THRESHOLD_NO_DETECTED_SECONDS')),
            'detect_label': set(os.environ.get('DETECT_LABEL').split(',')),
            'pause_seconds': int(os.environ.get('PAUSE_SECONDS')),
            'black_screen_seconds': int(os.environ.get('BLACK_SCREEN_SECONDS')),
        }
        return conf
