FROM python:3.6-alpine
LABEL maintainer="Tim Kolotov <timophey.kolotov@gmail.com>"

RUN pip install google-api-python-client oauth2client pytz requests && \
    apk update && apk add gnupg xz tzdata

COPY app/ /opt/

ENV IN_DOCKER=1
WORKDIR "/opt/"

CMD ["python", "backup.py", "--noauth_local_webserver"]
