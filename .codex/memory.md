# Память проекта

- Фактическая структура компонентов, поток mesh, сборка и проверки описаны в
  [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md); при расхождении сверяться с
  кодом, workflows и платформенными README.
- Android live-калибровка и настройки сопла находятся в `LiveBedMesh.kt` и
  `NozzleSettings.kt`; границы SSH-потока и поведения описаны в архитектуре.
- macOS live-калибровка, вкладка сопла и SSH-команды находятся в `mac/app.py`,
  `mac/core/live_mesh.py`, `mac/core/ssh_client.py` и `mac/ui/components/nozzle_tab.py`;
  обзор платформенного паритета поддерживается в `docs/ARCHITECTURE.md`.
- Подтверждённые границы хранения и применения настроек сопла Windows собраны в
  [nozzle-ui-notes.md](nozzle-ui-notes.md), по реализации и профильным тестам.
- Анализ штатного K3SysUi — исторический; его ограничения описаны в
  [k3sysui-analysis-2026-08-27.md](k3sysui-analysis-2026-08-27.md). Состояние
  конкретного принтера всегда требует актуального чтения устройства.
