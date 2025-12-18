FROM python:3.12-alpine

# устанавливаем переменные окружения
ENV HOME=/home/fast \
    APP_HOME=/home/fast/app \
    PYTHONPATH="$PYTHONPATH:/home/fast" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p $APP_HOME \
  && addgroup -S fast \
  && adduser -S fast -G fast

WORKDIR $HOME

COPY app app
COPY requirements.txt alembic.ini .env .

RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && chown -R fast:fast .

USER fast