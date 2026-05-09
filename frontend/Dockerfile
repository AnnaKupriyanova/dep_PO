FROM nginx:alpine

# Копируем HTML
COPY index.html /usr/share/nginx/html/index.html

# Копируем всю статику (CSS, JS, изображения)
COPY static /usr/share/nginx/html/static

# Копируем конфиг Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80