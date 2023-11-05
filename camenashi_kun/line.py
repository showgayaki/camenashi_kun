from linebot.v3.messaging import Configuration, MessagingApi, ApiClient, PushMessageRequest, ApiException
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
    スタンプID: https://devdocs.line.me/files/sticker_list.pdf
    """
    def __init__(self, access_token):
        self.api_url = 'https://notify-api.line.me/api/notify'
        self.headers = {'Authorization': 'Bearer ' + access_token}

    def send_message(self, payload, image=None):
        files = {}
        if image is not None:
            files = {'imageFile': open(image, 'rb')}

        try:
            res = requests.post(self.api_url, headers=self.headers, data=payload, files=files)
            status_code = res.status_code
        except Exception as e:
            return {'error': str(e)}
        else:
            res.close()
            return {'info': 'StatusCode: {}'.format(status_code)}


class LineMessagingApi:
    def __init__(self, access_token):
        self.configuration = Configuration(
            access_token=access_token
        )

    def send_message(self, to, message_dict):
        message_dict['to'] = to

        with ApiClient(self.configuration) as api_client:
            # Create an instance of the API class
            api_instance = MessagingApi(api_client)
            push_message_request = PushMessageRequest.from_dict(message_dict)

            try:
                push_message_result = api_instance.push_message_with_http_info(push_message_request, _return_http_data_only=False)
                return {'info': f'StatusCode: {push_message_result.status_code}'}
            except ApiException as e:
                return {'error': 'Exception when calling MessagingApi->push_message: %s\n' % e}
