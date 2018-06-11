FROM python:2.7-alpine
LABEL maintainer="Tim Kolotov <timophey.kolotov@gmail.com>"

RUN pip install google-api-python-client oauth2client && \
    apk update && apk add gnupg xz

COPY app/backup.py /opt/backuper.py

ENV IN_DOCKER=1
WORKDIR "/opt/"

CMD ["python", "backuper.py", "--noauth_local_webserver"]
