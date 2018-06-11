import os
import time
import json
from datetime import datetime
from subprocess import Popen, PIPE

from apiclient import discovery, http
from httplib2 import Http
from oauth2client import file, client, tools


def setup_api():
    """ Setup the Drive v3 API """

    scopes = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_id.json', scopes)
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
    file_body = http.MediaFileUpload(filename, 'application/octet-stream')
    try:
        SERVICE.files().create(body=metadata, media_body=file_body).execute()
    except http.HttpError:
        return False
    else:
        return True


def make_backup(files, name, passphrase):
    if os.environ.get('IN_DOCKER', False):
        # make relative path to files and change dir
        files = map(lambda x: '.' + x, files)
        os.chdir('/opt/backup')

    # preset commands for making backup
    cmd = {
        'tar': ['tar', '-c'] + files,
        'xz_': ['xz', '-1'],
        'gpg': ['gpg', '-c', '--batch', '--passphrase', passphrase],
    }

    # run sub processes
    p1 = Popen(cmd['tar'], stdout=PIPE)
    p2 = Popen(cmd['xz_'], stdin=p1.stdout, stdout=PIPE)
    p3 = Popen(cmd['gpg'], stdin=p2.stdout, stdout=PIPE)

    name = '%s-%s.tar.xz.gpg' % (name, datetime.now().strftime('%Y%m%d-%H%M'))
    with open('/tmp/' + name, 'wb') as backup_file:
        backup_file.write(p3.communicate()[0])

    return backup_file.name


if __name__ == '__main__':
    with open('./config.json', 'r') as config_file:
        config = json.load(config_file)

    # must be global
    DRIVE_DIRS = config['drive_path'].split('/')[1:]
    SERVICE = setup_api()

    # create backup
    path_to_backup_file = make_backup(
        config['files'], config['name'], config['passphrase'])

    # determine Google Drive directory id for uploading backup file
    directory_id = get_dir_id()

    # upload backup file and remove local file
    upload_result = upload_backup(directory_id, path_to_backup_file)
    if upload_result:
        os.unlink(path_to_backup_file)
