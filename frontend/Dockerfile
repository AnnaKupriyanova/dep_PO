# frontend/Dockerfile
FROM python:3.11-slim

WORKDIR /usr/share/nginx/html

COPY ./static ./static
COPY ./templates ./templates
COPY ./templates/index.html ./index.html
COPY ./templates/model.html ./model.html

EXPOSE 3000

CMD ["python", "-m", "http.server", "3000"]