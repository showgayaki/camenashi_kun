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
                'messaging_api_limit': int(os.getenv('LINE_MESSAGING_API_LIMIT')),
                'is_notified_reached_limit': True if os.getenv('IS_NOTIFIED_REACHED_LIMIT') == 'True' else False,
                'is_notified_ping_error': True if os.getenv('IS_NOTIFIED_PING_ERROR') == 'True' else False,
            },
            'camera': {
                'ip': os.getenv('CAMERA_IP'),
                'user': os.getenv('CAMERA_USER'),
                'pass': os.getenv('CAMERA_PASS')
            },
            'movie_speed': int(os.getenv('MOVIE_SPEED')),
            'notice_threshold': int(os.getenv('NOTICE_THRESHOLD')),
            'threshold_no_detected_seconds': int(os.getenv('THRESHOLD_NO_DETECTED_SECONDS')),
            'detect_label': os.getenv('DETECT_LABEL'),
            'detect_area': [int(i) for i in os.getenv('DETECT_AREA').split(',')],
            'pause_seconds': int(os.getenv('PAUSE_SECONDS')),
            'black_screen_seconds': int(os.getenv('BLACK_SCREEN_SECONDS')),
            's3_bucket_name': os.getenv('S3_BUCKET_NAME'),
            's3_expires_in': int(os.getenv('S3_EXPIRES_IN')),
            'ssh': {
                'hostname': os.getenv('SSH_HOSTNAME'),
                'upload_dir': os.getenv('SSH_UPLOAD_DIR'),
                'threshold_storage_days': int(os.getenv('THRESHOLD_STORAGE_DAYS')),
            }
        }
        return conf

    def update_value(self, key, after):
        before = os.environ[key]

        str_value = str(after)
        dotenv.set_key(self.dotenv_path, key, str_value)
        os.environ[key] = str_value

        return self.fetch_config(), before, after
