# BedMesh Visualizer (Android)

Android-версия Bed Mesh Visualizer на **Kotlin + Jetpack Compose**.

## Что уже реализовано
- **SSH загрузка** `printer.cfg` по IP/порт/логин/пароль/путь
- **Fallback**: если в `printer.cfg` нет points, пытаемся скачать `/userdata/app/gk/printer_mutable.cfg`
- Парсинг bed_mesh из:
  - JSON (`printer_mutable.cfg` часто в таком виде)
  - обычного cfg (`[bed_mesh ...]`, `probe_count`, `mesh_min/mesh_max`, многострочный `points`)
- **Config-редактор** (упрощённый):
  - редактирование параметров в секциях `[bed_mesh]` и `[filament_hub]`
  - сохранение на принтер по SSH с созданием бекапа перед отправкой
  - список/создание/восстановление/удаление бекапов `<printer.cfg>.bedmesh_bak_*`
- Визуализация:
  - **2D heatmap** (таблица значений)
  - лёгкая **псевдо-3D** изометрия (без OpenGL)
- Статистика (min/max/range/mean/var/rms) + коррекции 3 точек
- Проверка обновлений через GitHub Releases (кнопка открывает страницу релиза)

## Как запустить
1. Откройте папку `android` в Android Studio.
2. Дождитесь Gradle Sync (Android Studio скачает нужные компоненты).
3. Запустите модуль `app` на устройстве/эмуляторе.

> В репозитории **не добавлен Gradle Wrapper** (`gradlew`/`gradle-wrapper.jar`), потому что это бинарники.
> Если захотите собирать из консоли без Android Studio — сгенерируйте wrapper в Android Studio или установите Gradle.

