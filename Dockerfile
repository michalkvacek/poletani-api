FROM python:3.11-alpine

RUN apk update && \
    apk add --no-cache tzdata mariadb-client mariadb-dev && \
    pip install --upgrade pip
# protoze xfs uzivatel ma id=33
RUN deluser xfs

# uzivatel www-data v alpine neexistuje
RUN delgroup www-data && addgroup -g 33 -S www-data && adduser -u 33 -D -S -G www-data www-data


COPY requirements.txt /app/requirements.txt

# required packages for pip (becasue of yarl lib)
ENV INSTALL_PACKAGES build-base linux-headers

RUN apk add --no-cache $INSTALL_PACKAGES
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN apk del $INSTALL_PACKAGES

RUN mkdir /app/upload -p
COPY . /app

WORKDIR /app

CMD ["uvicorn", "src.asgi:app", "--reload", "--port=8000", "--host=0.0.0.0", "--log-level=debug"]