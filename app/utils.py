import re
import time
from urllib import parse

import httplib2


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
        func(parse.quote(f'B2GD: {message}'))

    def mock(self, message):
        pass

    def clickatell(self, message):
        url = 'http://api.clickatell.com/http/sendmsg?user={user}&' \
              'password={pass}&api_id={api_id}&to={subject}&text={msg}'

        h = httplib2.Http()
        response, content = h.request(url.format(**self.config, msg=message))
        if not response.status == 200 and content.decode()[:2] == 'ID':
            error = re.findall(r'<p[^>]*>([^<]+)<br />', content.decode())
            print_log(f'Sending notify error: {error[0]}')
        else:
            print_log(f'Notification to {self.config["subject"]} delivered')
