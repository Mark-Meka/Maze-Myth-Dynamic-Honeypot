FROM openresty/openresty:1.25.3.1-alpine

COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY lua/ /etc/nginx/lua/

EXPOSE 80

CMD ["openresty", "-g", "daemon off;"]
