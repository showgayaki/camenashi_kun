import os
import dotenv
from dotenv import load_dotenv


class Env:
    def __init__(self) -> None:
        load_dotenv(override=True)
        self._load()

    def _load(self) -> None:
        self.APP_NAME = 'Camenashi Kun'
        self.IS_NOTIFIED_PING_ERROR = True if os.getenv('IS_NOTIFIED_PING_ERROR') == 'True' else False

        self.CAMERA_IP = os.getenv('CAMERA_IP')
        self.CAMERA_USER = os.getenv('CAMERA_USER')
        self.CAMERA_PASS = os.getenv('CAMERA_PASS')

        self.MOVIE_SPEED = int(os.getenv('MOVIE_SPEED'))
        self.NOTICE_THRESHOLD = int(os.getenv('NOTICE_THRESHOLD'))
        self.THRESHOLD_NO_DETECTED_SECONDS = int(os.getenv('THRESHOLD_NO_DETECTED_SECONDS'))
        self.DETECT_LABEL = os.getenv('DETECT_LABEL')
        self.DETECT_AREA = [int(i) for i in os.getenv('DETECT_AREA').split(',')]
        self.PAUSE_SECONDS = int(os.getenv('PAUSE_SECONDS'))
        self.BLACK_SCREEN_SECONDS = int(os.getenv('BLACK_SCREEN_SECONDS'))

        self.SSH_HOSTNAME = os.getenv('SSH_HOSTNAME')
        self.SSH_UPLOAD_DIR = os.getenv('SSH_UPLOAD_DIR')
        self.THRESHOLD_STORAGE_DAYS = int(os.getenv('THRESHOLD_STORAGE_DAYS'))

        self.DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
        self.EMOJI_API_URL = os.getenv('EMOJI_API_URL')
        self.MENTION_ID = os.getenv('MENTION_ID')

    def update_value(self, key: str, after) -> tuple[str, object]:
        before = os.environ[key]

        str_value = str(after)
        dotenv_file = dotenv.find_dotenv()
        dotenv.set_key(dotenv_file, key, str_value)
        os.environ[key] = str_value

        load_dotenv(override=True)
        self._load()
        return before, after
