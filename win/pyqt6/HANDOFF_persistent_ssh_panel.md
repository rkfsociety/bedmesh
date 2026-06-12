# Задача: добавить в приложение функцию «Установить постоянный SSH + веб-панель»

## Что это и зачем

Приложение — Bed Mesh Visualizer (PyQt6) для принтера **Anycubic Kobra S1** на прошивке
GoKlipper. Оно уже умеет SSH/SFTP к принтеру (`core/ssh_client.py`, paramiko,
`192.168.0.197:2222`, `root/rockchip`).

На этом принтере **SSH по умолчанию работает только с USB-флешки**: при загрузке прошивка
разворачивает dropbear в `/tmp/ssh` из swu-пакета на флешке и стартует его. Без флешки после
перезагрузки SSH пропадает. Также на принтере поднята **лёгкая веб-панель статуса печати**
(бинарник `gkbridge`, отдаёт прогресс/слой/время/температуры на `http://<ip>:8088/`).

**Нужно:** кнопка в приложении, которая разово ставит на принтер **постоянный автозапуск**
(переживающий перезагрузку) и SSH, и веб-панели — чтобы флешка больше не была нужна.
Всё это уже сделано вручную по SSH; задача — упаковать те же шаги в функцию приложения.

---

## Как это работает (механизм, который нужно воспроизвести)

Загрузочная цепочка принтера:
`inittab → /etc/init.d/rcS → /etc/init.d/S90_app_run → /userdata/app/kenv/run.sh → ./start.sh`

`run.sh` лежит в **`/userdata`** (персистентно между ребутами, НО затирается OTA-обновлением
прошивки). В него вставляется одна строка-хук, которая при каждой загрузке вызывает
`/useremain/boot.sh`. А `boot.sh` уже поднимает dropbear и `gkbridge`.

Постоянные артефакты кладутся в **`/useremain`** (переживает и ребут, и OTA):
- `/useremain/ssh/` — пакет dropbear (бинарник + uClibc-библиотеки + хост-ключ)
- `/useremain/gkbridge` — бинарник веб-панели (Go, armv7, статический)
- `/useremain/boot.sh` — стартовый скрипт

### ⚠️ КРИТИЧЕСКАЯ ГРАБЛЯ (не повторять старую ошибку)

У бинарника `dropbear` **ELF-интерпретатор зашит ЖЁСТКО на `/tmp/ssh//ld-uClibc`**
(проверка: `strings /useremain/ssh/dropbear | grep ld-uClibc`). Поэтому его НЕЛЬЗЯ запускать
напрямую из `/useremain/ssh` — будет `not found` (нет загрузчика по зашитому пути), dropbear
залистенит порт, но будет рвать каждое соединение ДО SSH-баннера
(`kex_exchange_identification: read: Connection reset`).

**Правильно:** `boot.sh` сначала копирует пакет `cp -a /useremain/ssh/* /tmp/ssh/`, и только
потом запускает `/tmp/ssh/dropbear` — тогда `/tmp/ssh//ld-uClibc` существует. Ровно так же
делает штатный `update.sh` с флешки.

---

## Артефакты, которые нужно положить рядом с приложением

### 1. Бинарник `gkbridge` (веб-панель)

Готовый бинарник (armv7 Linux, ~5.7 МБ) лежит здесь:
`F:\github\BackupKobraS1\home\webpanel\bridge\gkbridge`
Исходник (Go, stdlib, HTML вшит через go:embed):
`F:\github\BackupKobraS1\home\webpanel\bridge\gkbridge.go` (+ `index.html`).

Скопировать бинарник в ресурсы приложения, например `resources/gkbridge`, и **включить его в
сборку PyInstaller** (добавить в `datas` в `.spec`). В рантайме путь брать через
`sys._MEIPASS`-aware хелпер (см. как приложение уже находит `icon.ico`).

Пересборка бинарника при необходимости (нужен Go, есть в `F:\github\PROG\go`):
```
cd F:\github\BackupKobraS1\home\webpanel\bridge
$env:GOOS="linux"; $env:GOARCH="arm"; $env:GOARM="7"
go build -ldflags="-s -w" -o gkbridge gkbridge.go
```

### 2. Скрипт `boot.sh`

Загружается на принтер как `/useremain/boot.sh`. Точное содержимое (LF-окончания!):

```sh
#!/bin/sh
# Постоянный автозапуск при загрузке: SSH (dropbear) + веб-панель (gkbridge).
# dropbear имеет ELF-интерпретатор зашитый на /tmp/ssh//ld-uClibc, поэтому
# разворачиваем пакет в /tmp/ssh и запускаем оттуда (как update.sh с флешки).
SRC=/useremain/ssh
SSH_DIR=/tmp/ssh

# SSH: развернуть пакет в /tmp/ssh и поднять dropbear, если порт 2222 свободен
# (08AE = 2222 в /proc/net/tcp; если флешка вставлена — порт занят, пропускаем).
if ! grep -q '00000000:08AE' /proc/net/tcp 2>/dev/null; then
    mkdir -p "$SSH_DIR"
    cp -a "$SRC"/* "$SSH_DIR"/ 2>/dev/null
    chmod +x "$SSH_DIR/dropbear" "$SSH_DIR/ld-uClibc" "$SSH_DIR/sftp-server" 2>/dev/null
    LD_LIBRARY_PATH="$SSH_DIR" "$SSH_DIR/dropbear" -F -E -a -p 2222 \
        -P "$SSH_DIR/dropbear.pid" -r "$SSH_DIR/dropbear_rsa_host_key" \
        >>/tmp/dropbear.log 2>&1 &
fi

# Веб-панель, если ещё не запущена
if ! ps | grep -v grep | grep -q /useremain/gkbridge; then
    chmod +x /useremain/gkbridge 2>/dev/null
    nohup /useremain/gkbridge >/tmp/gkbridge.out 2>&1 &
fi
```

(Эталон в репо принтера: `F:\github\BackupKobraS1\home\printer\boot\boot.sh`.)

---

## Что должна делать функция установки (последовательность по SSH)

Выполнять, пока SSH **уже работает** (т.е. флешка сейчас вставлена ИЛИ постоянный SSH уже
стоит). Все шаги **идемпотентны** — функцию можно жать повторно.

1. **Скопировать SSH-пакет в постоянное место** (источник — живой `/tmp/ssh`, он гарантированно
   есть, раз мы сейчас по SSH подключены):
   ```sh
   [ -d /useremain/ssh ] || cp -a /tmp/ssh /useremain/ssh
   ```
   (Если `/useremain/ssh` уже есть — не трогаем; пакет неизменен.)

2. **Залить `gkbridge`** через SFTP в `/useremain/gkbridge`, затем `chmod +x`.
   (Заливать всегда — чтобы обновлять бинарник; либо сравнить sha256, как уже делает
   `sha256_remote_file_via_sftp` в `ssh_client.py`.)

3. **Залить `boot.sh`** через SFTP в `/useremain/boot.sh` (или записать heredoc'ом), `chmod +x`.
   Важно: **LF-окончания строк** (не CRLF).

4. **Вставить хук в `run.sh`** (идемпотентно, с бэкапом):
   ```sh
   F=/userdata/app/kenv/run.sh
   grep -q '/useremain/boot.sh' "$F" || {
       cp -a "$F" "$F.bedmesh_bak_$(date +%Y%m%d_%H%M%S)"
       # вставить строку хука ПЕРЕД './start.sh'
       sed -i 's#^\./start\.sh#[ -f /useremain/boot.sh ] \&\& sh /useremain/boot.sh\n./start.sh#' "$F"
   }
   ```
   Хук-строка (если делать вставку не sed'ом, а программно):
   `[ -f /useremain/boot.sh ] && sh /useremain/boot.sh`
   Она ОБЯЗАНА стоять до строки `./start.sh` (после неё идёт `exit 0`, т.е. в конец файла
   дописывать нельзя — не выполнится). Проверить busybox-sed на принтере; если `\n` в replace
   не поддерживается — вставлять через `i\` или перечитать файл по SFTP, вставить строку в
   Python и залить обратно (надёжнее всего; ровно так это и делалось вручную).

5. **(Опционально) поднять прямо сейчас**, без ожидания ребута:
   ```sh
   sh /useremain/boot.sh
   ```
   dropbear на 2222 уже работает (флешка) → boot.sh его пропустит, но gkbridge поднимется
   сразу, и панель станет доступна без перезагрузки.

6. **Проверка/обратная связь пользователю:** после установки показать сообщение:
   «Готово. Можно вынуть флешку и перезагрузить принтер — SSH (2222) и панель
   (http://<ip>:8088/) поднимутся сами». Опционально проверить доступность панели HTTP-запросом
   `GET http://<ip>:8088/health` (ответ `ok`).

---

## Как удалить (для полноты — кнопка «Убрать автозапуск»)

```sh
# вынуть хук из run.sh
sed -i '/\/useremain\/boot.sh/d' /userdata/app/kenv/run.sh
# остановить процессы
kill $(cat /tmp/dropbear.pid 2>/dev/null) 2>/dev/null   # осторожно: оборвёт текущую SSH-сессию!
killall gkbridge 2>/dev/null
# удалить артефакты (по желанию)
rm -rf /useremain/ssh /useremain/gkbridge /useremain/boot.sh
```
NB: убийство dropbear оборвёт собственное соединение — лучше просто убрать хук и сказать
пользователю, что после ребута без флешки SSH не поднимется.

---

## Интеграция в приложение (конкретно)

- **`core/ssh_client.py`** — добавить функцию `install_persistent_ssh_and_panel(ip, port,
  user, password, gkbridge_local_path, progress_cb=None) -> bool`. Внутри: `get_ssh_connection`
  (уже есть), `exec_command` для шагов 1/4/5, `sftp.put` для шагов 2/3. Логировать через
  существующий `logger`. Использовать уже имеющийся `_sh_quote` для путей.
- **Хук в run.sh лучше вставлять Python'ом**, а не sed: `sftp.get('/userdata/app/kenv/run.sh')`
  → если нет `/useremain/boot.sh` в тексте, вставить строку перед `./start.sh`, сохранить с
  `\n` (LF) → `sftp.put` обратно (предварительно сделав бэкап через уже существующий
  `create_remote_backup`, но он завязан на маску `bedmesh_bak` — подойдёт).
- **UI** — добавить кнопку «Постоянный SSH + панель» в `ui/panels/left_panel.py` (рядом с
  SSH-полями). Запускать установку **в рабочем потоке** (как уже сделаны SSH-операции в
  `center_tabs.config_editor` через сигналы `ssh_operation_finished`/`ssh_download_succeeded`),
  чтобы не вешать GUI. По завершении — QMessageBox с инструкцией про флешку/ребут.
- **Параметры подключения** брать из `settings.json` (`ssh_ip/ssh_port/ssh_user/ssh_pass`),
  как остальной SSH-функционал.
- **PyInstaller** — в `Bed.Mesh.Visualizer.spec` добавить `gkbridge` в `datas`
  (`('resources/gkbridge', 'resources')`), путь в рантайме резолвить относительно `sys._MEIPASS`.

---

## Важные предупреждения (донести до пользователя в UI/доке)

1. **OTA-обновление прошивки затирает `/userdata/app/kenv/run.sh`** → хук пропадает →
   автозапуск отваливается. Сам payload в `/useremain` (ssh-пакет, gkbridge, boot.sh)
   обновление переживает. **Решение:** после обновления прошивки нажать кнопку установки ещё
   раз — она идемпотентно вернёт только строку-хук. (Можно при старте приложения проверять
   наличие хука и предлагать «переустановить».)
2. **Хост-ключ SSH** берётся из текущего `/tmp/ssh` (тот же, что на флешке), поэтому
   предупреждения о смене ключа у клиента не будет. Постоянный fingerprint:
   `ssh-rsa SHA256:MUT4OEEVmJPCZFDA30yy38F1jEOc4Xx00vkeQ2cqEUE`.
3. Порт SSH — **2222** (не 22). Веб-панель — **8088**.

---

## Чек-лист приёмки

- [ ] `gkbridge` забундлен в сборку и заливается на принтер.
- [ ] `boot.sh` на принтере с LF-окончаниями, разворачивает /tmp/ssh из /useremain/ssh.
- [ ] Хук в `run.sh` стоит ПЕРЕД `./start.sh`, не дублируется при повторной установке, есть бэкап.
- [ ] После «вынуть флешку + ребут»: `ssh -p 2222 root@<ip>` логинится (реальный вход, не просто
      открытый порт!), `http://<ip>:8088/` отдаёт панель.
- [ ] Повторное нажатие кнопки не ломает (идемпотентность).

Эталонные рабочие файлы и полная история — в репо `rkfsociety/BackupKobraS1`:
`home/printer/boot/` (boot.sh, run.sh с хуком) и `home/webpanel/` (gkbridge.go, index.html, README).
