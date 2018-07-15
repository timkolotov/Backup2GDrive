import time
from urllib import parse, request


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
        func(parse.quote(f'{message}'))

    def mock(self, message):
        pass

    def clickatell(self, msg: str):
        data = {
            "text": msg if self.config['sender_id'] else 'B2GD: ' + msg,
            "user": self.config['user'],
            "password": self.config['pass'],
            "api_id": self.config['api_id'],
            "to": self.config['subject']
        }
        if self.config['sender_id']:
            data.update({"from": self.config['sender_id']})

        params = parse.urlencode(data, safe='/!')
        url = 'http://api.clickatell.com/http/sendmsg'

        response = request.urlopen(url + '?' + params)
        response_body = response.read().decode()
        if not response.status == 200 or response_body[:2] != 'ID':
            print_log(f'Sending notify error: {response_body}')
        else:
            print_log(f'Notification to {self.config["subject"]} delivered')
