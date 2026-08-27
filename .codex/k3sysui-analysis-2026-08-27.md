# Анализ K3SysUi — 2026-08-27

- Экспериментальные копии `v6`–`v12` после полного перезапуска зависали на старте UI; восстановление выполнялось через штатный USB-SWU.
- В `v6`–`v10` внедрённый код находился в незамапленном промежутке ELF: первый исполняемый `PT_LOAD` заканчивался на виртуальном адресе `0x67c784`, с которого начинался патч.
- В `v10` были исправлены смещения вызовов `BL`, но этого было недостаточно из-за незамапленного сегмента.
- В `v11` первый `R-X` сегмент ELF был расширен, однако live-запуск всё равно завершался зависанием.
- В `v12` исправлена логика условного перехода в `AcSettingNozzleSelect`: для штатных индексов восстанавливался `mov r1,r2`, а строка `1.0` переносилась из зоны trampoline. Статическая проверка проходила, но live-запуск снова зависал.
- Последний отправленный файл: `K3SysUi.trial-add-1mm-both-v12-mapped`, MD5 `93a3a85ab6af19ef36f8be7675de85c0`. Перед заменой создана копия `/userdata/app/gk/K3SysUi.before-v12-20260827`.
- `start.sh` запускает `gklib`, `gkapi`, `K3SysUi` и `gkcam`; явной проверки MD5/подписи `K3SysUi` в нём не найдено.
- В `gklib` и `gkapi` присутствуют криптографические функции протокола, но это не подтверждает проверку файла UI.
- Официальный `ANYCUBIC-3D/Klipper-go` содержит backend-конфигурацию S1 (`nozzle_diameter`, PID и input-shaper), но исходников сенсорного UI `K3SysUi` не содержит.
- Следующий безопасный план: после восстановления снять свежие логи запуска и конфигурации, затем искать штатный API или ресурсный механизм расширения списка сопел. Прямое внедрение машинного кода остановлено до появления runtime-доказательств.

## Runtime-наблюдение штатной калибровки — 2026-08-27

- Во время штатной полной калибровки принтер не перезапускался; `gklib`, `gkapi`, `K3SysUi` и `gkcam` оставались запущены.
- `/tmp/gkui.log` зафиксировал последовательность: `Printer/ReportUIWorkStatus` с `busy:1`, затем `PidCalibrate/Extruder` с параметром `target:230`.
- `/tmp/gklib.log` подтвердил преобразование RPC в G-code: `PID_CALIBRATE HEATER=extruder TARGET=230 WRITE_FILE=0`; после 12 пиков калибровка завершилась, затем были записаны PID-параметры и вызван `SAVE_CONFIG`.
- Штатный UI получает фактические данные сопла через подписку `extruder`: `Nozzle_diameter: 0.4`, `Nozzle_material: hardened_steel`.
- На момент наблюдения `/userdata/app/gk/config/nozzle.cfg` содержал `material: "-"`, `diameter: "-"`, `modify: false`, тогда как `printer_mutable.cfg` содержал `nozzle_diameter: "0.40"` и `nozzle_material: "hardened_steel"`.
- Вывод: для будущего безопасного расширения нужно исследовать RPC/контроллер конфигурации и штатный ресурс UI; изменение только `nozzle.cfg` не является источником отображаемого состояния сопла.

## Runtime-срез полной калибровки после восстановления — 2026-08-27

- Снятие данных выполнялось только чтением по SSH, без перезапуска и без записи на принтер.
- После восстановления штатный `K3SysUi` имел MD5 `1bd84d3856b09a13a634143bb42378e5`; штатные процессы `gklib`, `gkapi`, `K3SysUi`, `gkcam` были запущены.
- Источники логов: `/tmp/gkui.log` и `/tmp/gklib.log`.
- При старте UI отправил `Query/Subscribe` для объекта `extruder`; RPC-статус вернул `Nozzle_diameter: 0.4` и `Nozzle_material: hardened_steel`.
- Полная цепочка, подтверждённая логами: `Printer/ReportUIWorkStatus busy=1` → `PidCalibrate/Extruder target=230` → G-code `PID_CALIBRATE HEATER=extruder TARGET=230 WRITE_FILE=0` → 12 пиков → `SAVE_CONFIG`.
- PID экструдера записан как `Kp=33.067`, `Ki=5.652`, `Kd=48.361`.
- Затем UI отправил `Resonance/SetShaperCalibrate` со скриптом `G28 W` и `SHAPER_CALIBRATE AXIS=x`; результат X: `3hump_ei`, `66.4`.
- Вторым запросом UI отправил `SHAPER_CALIBRATE AXIS=y`; результат Y: `2hump_ei`, `59.0`.
- После Y UI снова вызвал `Config/PrinterConfSave` с `SAVE_CONFIG`.
- На момент среза `nozzle.cfg` оставался `{material: "-", diameter: "-", modify: false}`, `printer.cfg` содержал `nozzle_diameter : 0.400`, а `printer_mutable.cfg` содержал `nozzle_diameter: "0.40"` и `nozzle_material: "hardened_steel"`.
- Ключевой вывод: отображение сопла и запуск калибровки связаны с RPC-статусом `extruder` и контроллером конфигурации; `nozzle.cfg` является отдельным флагом состояния и не единственным источником данных.
