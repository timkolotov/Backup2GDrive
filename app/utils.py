import time

import requests


def print_log(msg):
    data = dict(time=time.strftime('%Y-%m-%d %H:%M:%S'), msg=msg)
    print('[{time}] {msg}'.format(**data))


class Notify(object):
    def __init__(self, config):
        if config:
            self.driver = config['driver']
            self.config = config['config']
        else:
            self.driver = 'mock'

    def send(self, message: str):
        func = getattr(self, self.driver, self.mock)
        func(message)

    def mock(self, message):
        pass

    def clickatell(self, msg: str):
        url = 'https://api.clickatell.com/rest/message'
        data = {
            "text": msg if self.config.get('sender_id') else 'B2GD: ' + msg,
            "to": [self.config['subject']]
        }
        if self.config.get('sender_id'):
            data.update({"from": self.config['sender_id']})

        response = requests.post(url, json=data, headers={
            'Content-Type': 'application/json',
            'Authorization': f'bearer {self.config["api_token"]}',
            'Accept': 'application/json',
            'X-Version': '1'
        })
        if not response.status_code == 200 and not response.status_code == 202:
            error_description = response.json().get('error').get('description')
            print_log(f'Sending notify error: {error_description}')
        else:
            print_log(f'Notification to {self.config["subject"]} delivered')
