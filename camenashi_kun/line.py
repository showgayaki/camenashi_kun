from linebot.v3.messaging import Configuration, MessagingApi, ApiClient, PushMessageRequest, ApiException
import requests
import json


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

    def send_message(self, message, image=None):
        payload = {
            'message': message,
            'stickerPackageId': None,
            'stickerId': None
        }
        files = {}
        if image is not None:
            files = {'imageFile': open(image, 'rb')}

        try:
            res = requests.post(self.api_url, headers=self.headers, data=payload, files=files)
            status_code = res.status_code
            return {'level': 'info', 'detail': f'StatusCode: {status_code}'}
        except Exception as e:
            return {'level': 'error', 'detail': str(e)}
        finally:
            res.close()


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
                return {'level': 'info', 'detail': f'StatusCode: {push_message_result.status_code}'}
            except ApiException as e:
                return {'level': 'error', 'detail': 'Exception when calling MessagingApi->push_message: %s\n' % e}

    def message_quota_consumption(self):
        """
        https://developers.line.biz/ja/reference/messaging-api/#get-consumption
        https://github.com/line/line-bot-sdk-python/blob/master/linebot/v3/messaging/docs/MessagingApi.md#get_message_quota_consumption
        """
        with ApiClient(self.configuration) as api_client:
            # Create an instance of the API class
            api_instance = MessagingApi(api_client)

            try:
                api_response = api_instance.get_message_quota_consumption()
                api_response_json = json.loads(api_response.to_json())

                totalUsage = api_response_json['totalUsage'] if 'totalUsage' in api_response_json else None

                return {'level': 'info', 'detail': api_response_json, 'totalUsage': totalUsage}
            except ApiException as e:
                return {'level': 'error', 'detail': 'Exception when calling MessagingApi->get_message_quota_consumption: %s\n' % e}

    def group_member_count(self, to):
        """
        https://developers.line.biz/ja/reference/messaging-api/#get-members-group-count
        https://github.com/line/line-bot-sdk-python/blob/master/linebot/v3/messaging/docs/MessagingApi.md#get_group_member_count
        """
        with ApiClient(self.configuration) as api_client:
            # Create an instance of the API class
            api_instance = MessagingApi(api_client)

            try:
                api_response = api_instance.get_group_member_count(to)
                api_response_json = json.loads(api_response.to_json())

                count = api_response_json['count'] if 'count' in api_response_json else None

                return {'level': 'info', 'detail': api_response_json, 'count': count}
            except ApiException as e:
                return {'level': 'error', 'detail': 'Exception when calling MessagingApi->push_message: %s\n' % e}
