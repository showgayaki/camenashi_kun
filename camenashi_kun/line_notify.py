import requests


class LineNotify:
    """
    LINE通知用class
    https://notify-bot.line.me/ja/
        ログインして、[マイページ] - [トークンを発行する]
    payload = {
        'message': [メッセージ]
        , 'stickerPackageId': [STKPKGID]
        , 'stickerId': [STKID]
    }
    スタンプID：https://devdocs.line.me/files/sticker_list.pdf
    """
    def __init__(self, api_url, access_token):
        self.api_url = api_url
        self.headers = {'Authorization': 'Bearer ' + access_token}

    def send_message(self, payload, image):
        files = {}
        if image is not None:
            files = {'imageFile': open(image, 'rb')}

        try:
            res = requests.post(self.api_url, headers=self.headers, data=payload, files=files)
            status_code = res.status_code
        except Exception as e:
            return 'Error: {}'.format(e)
        else:
            res.close()
            return 'StatusCode: {}'.format(status_code)
