import time

from apiclient import discovery, http
from httplib2 import Http
from oauth2client import file, client, tools

from utils import print_log


class ApiClient(object):
    scopes = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('./conf.d/credentials.json')
    service = None
    drive_directory: str = None

    def __init__(self, drive_path: str):
        self.drive_dirs = drive_path.split('/')[1:]

    def setup(self):
        """ Setup the Drive v3 API """

        creds = self.store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(
                './conf.d/client_id.json', self.scopes)
            creds = tools.run_flow(flow, self.store)

        self.service = discovery.build(
            'drive', 'v3', http=creds.authorize(Http()))
        print_log('GDrive API client has been configured')

        # determine Google Drive directory id for uploading backup file
        self.drive_directory = self.get_dir_id()

    def upload_backup(self, filename):
        """ Upload backup file to GDrive """

        print_log('Uploading backup file is started')

        metadata = dict(
            name=filename.split('/').pop(), parents=[self.drive_directory])
        file_body = http.MediaFileUpload(
            filename, 'application/octet-stream', chunksize=1024*1024*2,
            resumable=True)
        try:
            self.service.files().create(
                body=metadata, media_body=file_body).execute()
        except http.HttpError:
            print_log('Uploading backup file is failed')
            return False
        else:
            print_log('Uploading backup file is finished successfully')
            return True

    def create_dir(self, dir_name, parent_id=None):
        """ Create new directory """

        metadata = {
            'name': dir_name,
            'parents': [parent_id if parent_id else 'root'],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        result = self.service.files().create(body=metadata).execute()
        dir_id = result.get('id', [])
        # start recursive creation if not find parent directory
        if len(self.drive_dirs) > 0:
            dir_id = self.create_dir(self.drive_dirs.pop(0), dir_id)
        return dir_id

    def get_dir_id(self, parent=None):
        """ Looking for specified path """

        query = "mimeType = 'application/vnd.google-apps.folder' and '{id}' " \
                "in parents and trashed = false and name = '{name}'"

        # if exception raised, then it was last directory - stop recursion
        try:
            current_dir = self.drive_dirs.pop(0)
        except IndexError:
            return parent

        result = self.service.files().list(
            q=query.format(id=parent if parent else 'root', name=current_dir)
        ).execute()
        time.sleep(.1)

        directories = result.get('files', [])
        if directories:
            dir_id = self.get_dir_id(parent=directories.pop().get('id'))
        else:
            dir_id = self.create_dir(current_dir, parent)
        return dir_id
