from pathlib import Path
import random
import requests


class Discord:
    def __init__(self, url: str) -> None:
        self.webhuook_url = url

    def post(self, content: str, files: list[Path] = []) -> dict:
        '''
        https://discord.com/developers/docs/resources/webhook
        '''
        # 連投するとアイコンなしになっちゃうので、ユーザー名を都度変えるために
        # ランダムな絵文字を前後に挿入しておく
        # これでユーザー名が被ることもほとんどないと思われ
        emoji1, emoji2 = self.choice_emoji(2)
        data = {
            'username': f'{emoji1}かめなしくん{emoji2}',
            'content': content,
        }

        multiple_files = []
        if len(files):
            for file in files:
                file_name = file.name
                with open(str(file), 'rb') as f:
                    file_binary = f.read()
                multiple_files.append(
                    (file_name, (file_name, file_binary))
                )

        try:
            response = requests.post(self.webhuook_url, data=data, files=multiple_files)
            return {'level': 'info', 'detail': f'StatusCode: {response.status_code}'}
        except Exception as e:
            return {'level': 'error', 'detail': e}

    def choice_emoji(self, number: int) -> list:
        emoji_list = [
            "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃",
            "🫠", "😉", "😊", "😇", "🥰", "😍", "🤩", "😘", "😗", "☺️",
            "☺", "😚", "😙", "🥲", "😋", "😛", "😜", "🤪", "😝", "🤑",
            "🤗", "🤭", "🫢", "🫣", "🤫", "🤔", "🫡", "🤐", "🤨", "😐",
            "😑", "😶", "🫥", "😶‍🌫️", "😶‍🌫", "😏", "😒", "🙄", "😬", "😮‍💨",
            "🤥", "🫨", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕",
            "🤢", "🤮", "🤧", "🥵", "🥶", "🥴", "😵", "😵‍💫", "🤯", "🤠",
            "🥳", "🥸", "😎", "🤓", "🧐", "😕", "🫤", "😟", "🙁", "☹️",
            "☹", "😮", "😯", "😲", "😳", "🥺", "🥹", "😦", "😧", "😨",
            "😰", "😥", "😢", "😭", "😱", "😖", "😣", "😞", "😓", "😩",
            "😫", "🥱", "😤", "😡", "😠", "🤬", "😈", "👿", "💀", "☠️",
            "☠", "💩", "🤡", "👹", "👺", "👻", "👽", "👾", "🤖", "😺",
            "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "🙈", "🙉",
            "🙊", "💋", "💯", "💢", "💥", "💫", "💦", "💨", "🕳️", "🕳",
            "💬", "👁️‍🗨️", "👁‍🗨️", "👁️‍🗨", "👁‍🗨", "🗨️", "🗨", "🗯️", "🗯", "💭",
            "💤"
        ]

        choices = random.sample(emoji_list, number)
        return choices
