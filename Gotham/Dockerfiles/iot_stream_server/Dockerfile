# using directly aler9/rtsp-simple-server fails ing GN3 for some reason...

#FROM aler9/rtsp-simple-server:v0.18.3 AS rtsp
FROM bluenviron/mediamtx:latest AS rtsp

FROM alpine
#COPY --from=rtsp /rtsp-simple-server /
#COPY rtsp-simple-server.yml /
#ENTRYPOINT [ "/rtsp-simple-server" ]

COPY --from=rtsp /mediamtx /
COPY rtsp-simple-server.yml /
ENTRYPOINT [ "/mediamtx" ]