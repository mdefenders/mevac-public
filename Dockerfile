ARG PYTHON_VERSION=3.12-slim-bookworm
FROM python:${PYTHON_VERSION}
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir
COPY mevac mevac
COPY mevaclibs mevaclibs
RUN mkdir /app/db && mkdir /app/posts

ENTRYPOINT ["/app/mevac"]