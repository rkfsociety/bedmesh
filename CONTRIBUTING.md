## Вклад в проект

Рабочая ветка проекта — `main`. Новые ветки, worktree и pull request не
создаются: изменения проверяются и коммитятся непосредственно в `main`, а
публикация выполняется прямым push в `origin/main` по явному запросу.

Перед изменениями:

```powershell
git switch main
git pull --ff-only origin main
git status --short --branch
```

Не перезаписывайте чужие незакоммиченные изменения. Если рабочее дерево
грязное или fast-forward невозможен, сначала разберите состояние вручную.

### Проверка изменений

```powershell
python win/pyqt6/run_tests.py
cd android; .\gradlew.bat :app:testDebugUnitTest; cd ..
cd webpanel; .\build.ps1; cd ..
```

### Релизы

Релизы делаются тегами (см. `readme.md`):

- `vX.YYY-win` — Windows
- `vX.YYY-mac` — macOS
- `vX.YYY-android` — Android

