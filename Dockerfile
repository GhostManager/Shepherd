FROM python:slim
EXPOSE 8000
WORKDIR /src
COPY . .
RUN pip install -r requirements.txt

CMD ["gunicorn", "shepherd.wsgi", "-b", "0.0.0.0:8000"]