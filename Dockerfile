FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

EXPOSE 80

CMD ["gunicorn", "--log-level", "debug", "--bind", "0.0.0.0:80", "app:app"]
