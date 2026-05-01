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
- Иконка лаунчера: исходник `android/icon.png` (копии в `app/src/main/res/mipmap-*`)

## Подпись release (один ключ на всех ПК)

За подпись отвечают **два файла** (их **нет в git**, храните у себя и копируйте на другой компьютер):

| Файл | Назначение |
|------|------------|
| `keystore/bedmesh-release.jks` | Сам **ключ** (хранилище PKCS12/JKS) |
| `keystore.properties` | Путь к JKS, **alias**, **пароли** store и key |

Структура на любом ПК должна быть такой:

```text
android/
  keystore.properties          ← рядом с settings.gradle.kts
  keystore/
    bedmesh-release.jks        ← имя как в storeFile внутри properties
```

Шаблон без секретов: `keystore.properties.example` → скопируйте в `keystore.properties` и подставьте значения.

Сборка release автоматически подписывается, если `keystore.properties` существует (см. `app/build.gradle.kts`).

```powershell
cd android
.\gradlew.bat :app:assembleRelease
```

APK: `app/build/outputs/apk/release/app-release.apk` (подписанный).

**Перенос на другой ПК:** склонируйте репозиторий, положите в `android/` те же `keystore.properties` и `keystore/*.jks`, создайте `local.properties` с `sdk.dir=...` (Android Studio сделает сама). Дальше `assembleRelease` — подпись будет той же.

**Безопасность:** не отдавайте никому `.jks` и `keystore.properties`; при утечке ключа любой сможет подписывать обновления вашим именем.

## Как запустить
1. Откройте папку `android` в Android Studio.
2. Дождитесь Gradle Sync (Android Studio скачает нужные компоненты).
3. Запустите модуль `app` на устройстве/эмуляторе.

> Сборка из консоли: в каталоге `android` есть `gradlew.bat` и Gradle Wrapper.

