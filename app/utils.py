import time


def print_log(msg):
    data = dict(time=time.strftime('%Y-%m-%d %H:%M:%S'), msg=msg)
    print('[{time}] {msg}'.format(**data))
