from linebot.v3.messaging import Configuration, MessagingApi, ApiClient, PushMessageRequest, ApiException


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
