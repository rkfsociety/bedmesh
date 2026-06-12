#!/bin/sh
# Выключить локальный стрим и вернуть штатную камеру приложения (gkcam).
# gkcam требует богатый LD_LIBRARY_PATH (libagora, librockit и т.п.), который
# выставляется на загрузке. Берём его у живого соседнего gk-процесса.
killall mjpg_streamer 2>/dev/null
sleep 1

LD=""
for d in /proc/[0-9]*; do
    cmd=$(tr '\0' ' ' < "$d/cmdline" 2>/dev/null)
    case "$cmd" in
        *gkapi*|*gklib*|*K3SysUi*)
            L=$(tr '\0' '\n' < "$d/environ" 2>/dev/null | grep '^LD_LIBRARY_PATH=')
            if [ -n "$L" ]; then LD="$L"; break; fi
            ;;
    esac
done
LDVAL=${LD#LD_LIBRARY_PATH=}
[ -z "$LDVAL" ] && LDVAL="/userdata/app/gk:/ac_lib/lib/third_lib:/ac_lib/lib"

# не плодим второй экземпляр
if ps | grep -v grep | grep -q '[g]kcam'; then
    echo CAM_OFF_OK
    exit 0
fi

cd /userdata/app/gk
LD_LIBRARY_PATH="/userdata/app/gk:$LDVAL" nohup ./gkcam >/tmp/gkcam.log 2>&1 &
sleep 2
if ps | grep -v grep | grep -q '[g]kcam'; then
    echo CAM_OFF_OK
else
    echo CAM_OFF_FAIL
    tail -5 /tmp/gkcam.log
fi
