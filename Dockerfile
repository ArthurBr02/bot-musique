FROM python:3.14-alpine

COPY requirements.txt .

# Build deps needed to compile asyncpg if no musllinux wheel is available
RUN apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

COPY . .

CMD ["python3", "run.py"]
