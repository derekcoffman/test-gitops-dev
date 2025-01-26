# FROM python:3.10-slim
FROM python:3.12-slim-bullseye
LABEL org.opencontainers.image.source="https://github.com/derekcoffman/verifier"


# WORKDIR /app
ENV APP_HOME /app
WORKDIR $APP_HOME

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY VERSION .
COPY ./verifier.py ./app.py

# CMD [ "python3", "verify.py" ]
CMD exec gunicorn --workers 1 --threads 8 --timeout 0 app:app
