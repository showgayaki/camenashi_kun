from pathlib import Path
from logging import getLogger
import random
import requests

from camenashi_kun import env


logger = getLogger(__name__)


class Discord:
    def __init__(self, url: str) -> None:
        self.webhuook_url = url
        self.timeout = (3, 6)

    def post(self, content: str, files: list[Path] = []) -> bool:
        '''
        https://discord.com/developers/docs/resources/webhook
        '''
        # 連投するとアイコンなしになっちゃうので、ユーザー名を都度変えるために
        # ランダムな絵文字を前後に挿入しておく
        # これでユーザー名が被ることもほとんどないと思われ
        emoji1, emoji2 = self._choice_emoji(2)
        data = {
            'username': f'{emoji1}かめなしくん{emoji2}',
            'content': content,
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
            logger.info('Starting post Discord.')
            response = requests.post(
                self.webhuook_url,
                data=data,
                files=multiple_files,
                timeout=self.timeout
            )
            logger.info(f'Status Code: {response.status_code}')
            if 200 <= response.status_code < 300:
                return True
        except Exception as e:
            logger.critical(e)

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
