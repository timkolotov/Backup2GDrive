import json
import os
import time
from subprocess import call

from api import ApiClient
from utils import print_log


def make_backup(files, exclude, name, passphrase, **kwargs):
    if os.environ.get('IN_DOCKER', False):
        # make relative path to files and change dir
        files = list(map(lambda x: '.' + x, files))
        # add dot only if it is absolute path
        exclude = list(map(lambda x: ('.' + x) if x[0] == "/" else x, exclude))
        os.chdir('/opt/backup')

    exclude = '' if not exclude else '--exclude ' + ' --exclude '.join(exclude)

    # preset commands for making backup
    commands = [
        'tar {ex} -c {files}'.format(files=' '.join(files), ex=exclude),
        'gpg -c --batch --passphrase %s' % passphrase
    ]

    # preset file extensions
    extensions = ['tar', 'gpg']

    # if compression enabled - add command and extension
    if kwargs.get('compression'):
        print_log('Making backup with compression is started.')
        commands.insert(1, 'xz -%s' % str(kwargs.get('compression')))
        extensions.insert(1, 'xz')
    else:
        print_log('Making backup without compression is started.')

    name = '{name}-{date}.{extensions}'.format(
        name=name,
        date=time.strftime('%Y%m%d-%H%M'),
        extensions='.'.join(extensions))

    print_log('Name of file {filename}'.format(filename=name))
    with open('/tmp/' + name, 'wb') as backup_file:
        exit_error = call(' | '.join(commands), shell=True, stdout=backup_file)

    if os.environ.get('IN_DOCKER', False):
        # return to opt directory
        os.chdir('/opt')
    print_log('Backup file is created')

    return backup_file.name if not exit_error else False


def exec_command(cmd):
    cmd_result = call(cmd, shell=True)
    if type(cmd_result) is int and cmd_result is not 0:
        exit(cmd_result)


if __name__ == '__main__':
    with open('./conf.d/config.json', 'r') as config_file:
        config = json.load(config_file)

    # configure time zone
    os.environ['TZ'] = config.pop('timezone', '')
    time.tzset()

    ac = ApiClient(path=config['drive_path'])
    ac.setup()

    if 'run_before' in config:
        print_log('Execution \'run_before\' command is started')
        exec_command(config['run_before'])

    # create backup
    path_to_backup_file = make_backup(**config)

    # upload backup file and remove local file
    upload_result = ac.upload_backup(path_to_backup_file)
    if upload_result:
        os.unlink(path_to_backup_file)

    if 'run_after' in config:
        print_log('Execution \'run_after\' command is started')
        exec_command(config['run_after'])
