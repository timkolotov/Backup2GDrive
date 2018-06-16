import os
import time
import json
import pytz
from datetime import datetime
from subprocess import call

from apiclient import discovery, http
from httplib2 import Http
from oauth2client import file, client, tools


def setup_api():
    """ Setup the Drive v3 API """

    scopes = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('./conf.d/credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('./conf.d/client_id.json', scopes)
        creds = tools.run_flow(flow, store)
    return discovery.build('drive', 'v3', http=creds.authorize(Http()))


def create_dir(dir_name, parent_id=None):
    """ Create new directory """

    metadata = {
        'name': dir_name,
        'parents': [parent_id if parent_id else 'root'],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    result = SERVICE.files().create(body=metadata).execute()
    dir_id = result.get('id', [])
    # start recursive creation if not find parent directory
    if len(DRIVE_DIRS) > 0:
        dir_id = create_dir(DRIVE_DIRS.pop(0), dir_id)
    return dir_id


def get_dir_id(parent=None):
    """ Looking for specified path """

    query = "mimeType = 'application/vnd.google-apps.folder' and '{id}' " \
            "in parents and trashed = false and name = '{name}'"

    # if exception raised, then it was last directory - stop recursion
    try:
        current_directory = DRIVE_DIRS.pop(0)
    except IndexError:
        return parent

    result = SERVICE.files().list(
        q=query.format(id=parent if parent else 'root', name=current_directory)
    ).execute()
    time.sleep(.1)

    directories = result.get('files', [])
    if directories:
        dir_id = get_dir_id(parent=directories.pop().get('id'))
    else:
        dir_id = create_dir(current_directory, parent)
    return dir_id


def upload_backup(directory, filename):
    """ Upload backup file to GDrive """

    metadata = {'name': filename.split('/').pop(), 'parents': [directory]}
    file_body = http.MediaFileUpload(filename, 'application/octet-stream',
                                     chunksize=1024*1024*2, resumable=True)
    try:
        SERVICE.files().create(body=metadata, media_body=file_body).execute()
    except http.HttpError:
        return False
    else:
        return True


def make_backup(files, exclude, name, passphrase, tz):
    if os.environ.get('IN_DOCKER', False):
        # make relative path to files and change dir
        files = map(lambda x: '.' + x, files)
        exclude = map(lambda x: '.' + x, exclude)
        os.chdir('/opt/backup')

    exclude = '' if not exclude else '--exclude ' + ' --exclude '.join(exclude)

    # preset commands for making backup
    cmd = 'tar {ex} -c {files} | xz -1 | gpg -c --batch --passphrase {pph}'.\
        format(files=' '.join(files), ex=exclude, pph=passphrase)

    name = '{name}-{date}.tar.xz.gpg'.format(
        name=name, date=datetime.now(tz).strftime('%Y%m%d-%H%M'))
    with open('/tmp/' + name, 'wb') as backup_file:
        exit_error = call(cmd, shell=True, stdout=backup_file)

    if os.environ.get('IN_DOCKER', False):
        os.chdir('/opt')

    return backup_file.name if not exit_error else False


def exec_command(cmd):
    cmd_result = call(cmd, shell=True)
    if type(cmd_result) is int and cmd_result is not 0:
        exit(cmd_result)


if __name__ == '__main__':
    with open('./conf.d/config.json', 'r') as config_file:
        config = json.load(config_file)

    # must be global
    DRIVE_DIRS = config['drive_path'].split('/')[1:]
    SERVICE = setup_api()

    try:
        timezone = pytz.timezone(config['timezone'])
    except KeyError:
        timezone = None

    if 'run_before' in config:
        exec_command(config['run_before'])

    # create backup
    path_to_backup_file = make_backup(
        config['files'],
        config.get('exclude', []),
        config['name'],
        config['passphrase'],
        timezone)

    # determine Google Drive directory id for uploading backup file
    directory_id = get_dir_id()

    # upload backup file and remove local file
    upload_result = upload_backup(directory_id, path_to_backup_file)
    if upload_result:
        os.unlink(path_to_backup_file)

    if 'run_after' in config:
        exec_command(config['run_after'])
