#!/bin/sh
# Включить локальный MJPEG-стрим камеры (mjpg_streamer на :8080).
# Камера используется монопольно, поэтому сначала глушим gkcam (облачную камеру
# приложения Anycubic). Вернуть всё обратно: cam-off.sh.
DIR=/useremain/camera
RES=${1:-1280x720}
PORT=${2:-8080}

# gkcam держит камеру — освобождаем
killall gkcam 2>/dev/null
killall mjpg_streamer 2>/dev/null
sleep 1

[ -e "$DIR/libjpeg.so.8" ] || ln -sf libjpeg.so.8.2.2 "$DIR/libjpeg.so.8"
chmod +x "$DIR/mjpg_streamer" 2>/dev/null
mkdir -p "$DIR/www"

# берём первую USB UVC-камеру по стабильному имени (как делает Rinkhals)
CAM=$(ls /dev/v4l/by-id/*-index0 2>/dev/null | head -1)
[ -z "$CAM" ] && CAM=/dev/video10

cd "$DIR"
LD_LIBRARY_PATH="$DIR" nohup ./mjpg_streamer \
    -i "$DIR/input_uvc.so -d $CAM -r $RES -n" \
    -o "$DIR/output_http.so -p $PORT -w $DIR/www" >/tmp/mjpg.log 2>&1 &

sleep 2
if ps | grep -v grep | grep -q mjpg_streamer; then
    echo CAM_ON_OK
else
    echo CAM_ON_FAIL
    tail -5 /tmp/mjpg.log
fi
