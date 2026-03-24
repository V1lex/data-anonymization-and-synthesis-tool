FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/site/index.html /usr/share/nginx/html/index.html
COPY src/sda/web/static/app.css /usr/share/nginx/html/static/app.css
COPY src/sda/web/static/app.js /usr/share/nginx/html/static/app.js