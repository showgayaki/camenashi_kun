import os
import dotenv
from dotenv import load_dotenv
from pathlib import Path


class Config:
    def __init__(self, root_dir):
        self.dotenv_path = Path(root_dir).resolve().joinpath('.env')

    def fetch_config(self):
        load_dotenv(self.dotenv_path)
        conf = {
            'app_name': 'Camenashi Kun',
            'line': {
                'notify_token': os.getenv('LINE_NOTIFY_ACCESS_TOKEN'),
                'messaging_api_token': os.getenv('LINE_MESSAGING_API_ACCESS_TOKEN'),
                'to': os.getenv('TO'),
                'messaging_api_limit': os.getenv('LINE_MESSAGING_API_LIMIT'),
                'is_notify_reached_limit': True if os.getenv('IS_NOTIFY_REACHED_LIMIT') == 'True' else False,
            },
            'camera': {
                'ip': os.getenv('CAMERA_IP'),
                'user': os.getenv('CAMERA_USER'),
                'pass': os.getenv('CAMERA_PASS')
            },
            'notice_threshold': int(os.getenv('NOTICE_THRESHOLD')),
            'threshold_no_detected_seconds': int(os.getenv('THRESHOLD_NO_DETECTED_SECONDS')),
            'detect_label': set(os.getenv('DETECT_LABEL').split(',')),
            'pause_seconds': int(os.getenv('PAUSE_SECONDS')),
            'black_screen_seconds': int(os.getenv('BLACK_SCREEN_SECONDS')),
            's3_bucket_name': os.getenv('S3_BUCKET_NAME'),
            's3_expires_in': int(os.getenv('S3_EXPIRES_IN')),
        }
        return conf

    def toggle_is_notify_reached_limit(self, value):
        str_value = str(value)
        dotenv.set_key(self.dotenv_path, 'IS_NOTIFY_REACHED_LIMIT', str_value)
        os.environ['IS_NOTIFY_REACHED_LIMIT'] = str_value

        return self.fetch_config(), not value, value
