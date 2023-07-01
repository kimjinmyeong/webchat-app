FROM python:3.11.4

WORKDIR /webchat
#RUN apk add --update --no-cache --virtual .tmp-build-deps \
#    gcc libc-dev linux-headers \
#    && apk add libffi-dev
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY server.py .
COPY /templates ./templates

CMD ["python3", "server.py"]