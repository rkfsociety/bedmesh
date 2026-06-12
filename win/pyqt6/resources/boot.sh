#!/bin/sh
# Постоянный автозапуск при загрузке принтера (без флешки):
#  - SSH-сервер dropbear (разворачивается из /useremain/ssh в /tmp/ssh и стартует)
#  - мост веб-панели gkbridge
# Лежит на принтере как /useremain/boot.sh, вызывается из /userdata/app/kenv/run.sh.
#
# ВАЖНО: у бинарника dropbear ELF-интерпретатор зашит жёстко на /tmp/ssh//ld-uClibc,
# поэтому он ОБЯЗАН запускаться из /tmp/ssh (как это делает update.sh с флешки).
# /useremain/ssh — постоянная копия пакета (переживает ребут и обновление прошивки).

SRC=/useremain/ssh
SSH_DIR=/tmp/ssh

# SSH: развернуть пакет в /tmp/ssh и поднять dropbear, если пакет установлен
# и порт 2222 свободен (08AE = 2222 в /proc/net/tcp). Если флешка вставлена —
# она уже заняла порт, пропускаем. Если /useremain/ssh нет (панель ставили
# отдельно) — тоже пропускаем.
if [ -d "$SRC" ] && ! grep -q '00000000:08AE' /proc/net/tcp 2>/dev/null; then
    mkdir -p "$SSH_DIR"
    cp -a "$SRC"/* "$SSH_DIR"/ 2>/dev/null
    chmod +x "$SSH_DIR/dropbear" "$SSH_DIR/ld-uClibc" "$SSH_DIR/sftp-server" 2>/dev/null
    LD_LIBRARY_PATH="$SSH_DIR" "$SSH_DIR/dropbear" -F -E -a -p 2222 \
        -P "$SSH_DIR/dropbear.pid" -r "$SSH_DIR/dropbear_rsa_host_key" \
        >>/tmp/dropbear.log 2>&1 &
fi

# мост веб-панели, если установлен и ещё не запущен
if [ -x /useremain/gkbridge ] && ! ps | grep -v grep | grep -q /useremain/gkbridge; then
    chmod +x /useremain/gkbridge 2>/dev/null
    nohup /useremain/gkbridge >/tmp/gkbridge.out 2>&1 &
fi
