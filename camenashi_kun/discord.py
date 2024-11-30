from pathlib import Path
from logging import getLogger
import random
import requests

from camenashi_kun import env


logger = getLogger(__name__)


class Discord:
    def __init__(self, url: str) -> None:
        self.webhook_url = url
        self.timeout = (3, 6)

    def post(self, content: str, files: list[Path] = [], mention_id=None) -> bool:
        '''
        https://discord.com/developers/docs/resources/webhook
        '''
        # 連投するとアイコンなしになっちゃうので、ユーザー名を都度変えるために
        # ランダムな絵文字を前後に挿入しておく
        # これでユーザー名が被ることもほとんどないと思われ
        emoji1, emoji2 = self._choice_emoji(2)
        data = {
            'username': f'{emoji1}かめなしくん{emoji2}',
            'content': f'<@{mention_id}> {content}' if mention_id else content,
        }

        multiple_files = []
        if len(files):
            logger.info(f'Post files: {files}.')
            for file in files:
                file_name = file.name
                with open(str(file), 'rb') as f:
                    file_binary = f.read()
                multiple_files.append(
                    (file_name, (file_name, file_binary))
                )

        try:
            logger.info('Starting Discord webhook post.')
            response = requests.post(
                self.webhook_url,
                data=data,
                files=multiple_files,
                timeout=self.timeout,
            )

            logger.info(f'Received status code: {response.status_code}')
            if 200 <= response.status_code < 300:
                logger.info('Discord webhook post successful.')
                return True
            else:
                logger.warning(f'Failed to post: {response.status_code}, {response.text}')
        except requests.exceptions.Timeout:
            logger.error("Request timed out.")
        except requests.exceptions.ConnectionError as ce:
            logger.error(f"Connection error: {ce}")
        except Exception as e:
            logger.critical(f"Unexpected error: {e}")

        return False

    def _choice_emoji(self, number: int) -> list:
        logger.info(f'Starting fetch emojis from {env.EMOJI_API_URL}')
        try:
            response = requests.get(env.EMOJI_API_URL, timeout=self.timeout)
            response.encoding = response.apparent_encoding
            emojis = response.json()
        except Exception as e:
            logger.critical(e)
            from emoji import emojis_local
            emojis = emojis_local

        # 指定した数分の絵文字をランダムに取得
        choices = random.sample(emojis, number)
        logger.info(f'Choiced emojis: {choices}')
        return choices
