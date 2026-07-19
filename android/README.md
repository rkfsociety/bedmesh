# Bed Mesh Visualizer (Android)

Android-клиент на **Kotlin + Jetpack Compose**.

Вкладки: **SSH** | **Карта** | **Config** | **Принтер** | **RAW**.

## Возможности

- **SSH**: загрузка `printer.cfg` по IP / порт / логин / пароль / путь
- **Fallback**: если в `printer.cfg` нет points — `/userdata/app/gk/printer_mutable.cfg`
- Парсинг bed_mesh из JSON (`printer_mutable.cfg`) и текстового cfg (`[bed_mesh ...]`, `probe_count`, `mesh_min` / `mesh_max`, многострочный `points`)
- **Карта**: 2D heatmap и псевдо-3D (Canvas, жест: drag — орбита, pinch — зум); статистика (min / max / range / mean / var / rms) и коррекции по 3 точкам
- **Config**: правка `[bed_mesh]`, `[filament_hub]`, температур leviQ3; сохранение по SSH с бекапом; список / создание / восстановление / удаление бекапов `<printer.cfg>.bedmesh_bak_*`
- **Принтер**:
  - установка **постоянного SSH** (dropbear в `/useremain/ssh`, автозапуск в `run.sh` — без флешки)
  - установка **веб-панели gkbridge** (скачивание с GitHub → `/useremain/gkbridge`, порт `8088`)
  - встроенный просмотр панели в WebView
- Проверка обновлений через GitHub Releases (скачивание APK)
- Иконка: исходник `android/icon.png` (копии в `app/src/main/res/mipmap-*`)

## Как запустить

1. Откройте папку `android` в Android Studio.
2. Дождитесь Gradle Sync.
3. Запустите модуль `app` на устройстве или эмуляторе.

Из консоли:

```powershell
cd android
.\gradlew.bat :app:assembleDebug
```

Нужен `local.properties` с `sdk.dir=...` (Android Studio создаёт сама).

## Release-сборка и подпись

Ключ подписи **лежит в репозитории**, чтобы release-APK с любой машины подписывался одинаково:

| Файл | Назначение |
|------|------------|
| `keystore/bedmesh-release.jks` | хранилище ключа (PKCS12/JKS) |
| `keystore.properties` | путь к JKS, alias, пароли store и key |
| `keystore.properties.example` | шаблон без секретов |

```text
android/
  keystore.properties
  keystore/
    bedmesh-release.jks
```

## CI / релизы

Тег `v*-android` (например `v0.170-android`) запускает GitHub Actions:
сборка `assembleRelease` (подпись из `keystore.properties` в репо) и публикация
`BedMeshVisualizer.apk` в GitHub Release.

Ручная сборка:

```powershell
cd android
.\gradlew.bat :app:assembleRelease
```

APK: `app/build/outputs/apk/release/app-release.apk`.

Сборка release подписывается автоматически, если `keystore.properties` на месте (см. `app/build.gradle.kts`).

**Безопасность:** файлы ключа публичны в этом репозитории намеренно (стабильная подпись обновлений). Не копируйте этот keystore в другие проекты и не считайте его «приватным секретом команды» — любой клон может им подписать APK.

## Связанные части репозитория

- Корневой обзор: [readme.md](../readme.md)
- Веб-панель на принтере: [webpanel/README.md](../webpanel/README.md)
