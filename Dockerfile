FROM python:3.12.14-alpine AS builder
WORKDIR /build
COPY scripts/build.py scripts/build.py
COPY media.json media.json
COPY public/ public/
RUN python scripts/build.py

FROM nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236
COPY --chmod=644 nginx-main.conf /etc/nginx/nginx.conf
COPY --chmod=644 nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist/reel-map.conf /etc/nginx/reel-map.conf
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /build/dist/site/ /usr/share/nginx/html/
RUN chmod -R a=rX /usr/share/nginx/html
USER 101:101
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
