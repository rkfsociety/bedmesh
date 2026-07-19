# Webpanel Bed Mesh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить во веб-панель просмотр текущей карты стола (bed mesh) с левым баром навигации и `GET /mesh`.

**Architecture:** gkbridge отдаёт отдельный `GET /mesh` (objects/query только `bed_mesh`, `probed_matrix`). UI: шапка+Пауза/Стоп всегда; слева вертикальный бар Печать/Стол; mesh грузится один раз при входе на вкладку и по кнопке «Обновить».

**Tech Stack:** Go 1 (stdlib), vanilla HTML/CSS/JS, сборка armv7 через `webpanel/build.ps1`.

## Global Constraints

- Версия панели: `1.9.0` в `webpanel/gkbridge.version`
- Матрица: только `probed_matrix`, не `mesh_matrix`
- Нет автополла `/mesh`
- Empty-state: «Карта стола не загружена» + подсказка про калибровку
- Ошибка сокета: UI-текст «нет связи с принтером»
- `/status` / `queryObjects` не расширять `bed_mesh`
- Макет-ориентир: `webpanel/mockup-mesh-tab.html`

## File map

| File | Role |
|---|---|
| `webpanel/mesh.go` | Парсинг ответа bed_mesh → JSON для `/mesh` |
| `webpanel/mesh_test.go` | Unit-тесты парсера |
| `webpanel/gkbridge.go` | Хендлер `GET /mesh` |
| `webpanel/index.html` | Layout (левый бар) + UI карты |
| `webpanel/gkbridge.version` | `1.9.0` |
| `webpanel/gkbridge` | Пересобранный armv7 бинарник |
| `webpanel/README.md` | Документировать `/mesh` |

---

### Task 1: Парсер bed_mesh + тесты

**Files:**
- Create: `webpanel/mesh.go`
- Create: `webpanel/mesh_test.go`

**Interfaces:**
- Produces: `type MeshResponse struct { OK bool; Profile string; MeshMin []float64; MeshMax []float64; Matrix [][]float64; Error string }`
- Produces: `func parseBedMeshStatus(statusJSON []byte) MeshResponse` — из `result.status` / сырого status с ключом `bed_mesh`

- [ ] **Step 1: Write failing tests**

```go
package main

import "testing"

func TestParseBedMeshOK(t *testing.T) {
	raw := []byte(`{"bed_mesh":{"profile_name":"default","mesh_min":[5,5],"mesh_max":[245,245],"probed_matrix":[[0.1,-0.2],[0.0,0.05]]}}`)
	r := parseBedMeshStatus(raw)
	if !r.OK || r.Profile != "default" || len(r.Matrix) != 2 || r.Matrix[0][1] != -0.2 {
		t.Fatalf("%+v", r)
	}
}

func TestParseBedMeshNoMesh(t *testing.T) {
	raw := []byte(`{"bed_mesh":{"profile_name":"","probed_matrix":[]}}`)
	r := parseBedMeshStatus(raw)
	if r.OK || r.Error != "no_mesh" {
		t.Fatalf("%+v", r)
	}
}

func TestParseBedMeshMissing(t *testing.T) {
	raw := []byte(`{}`)
	r := parseBedMeshStatus(raw)
	if r.OK || r.Error != "no_mesh" {
		t.Fatalf("%+v", r)
	}
}
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
cd F:\github\bedmesh\webpanel
$env:GOROOT="F:\github\PROG\go"; & "F:\github\PROG\go\bin\go.exe" test . -run TestParseBedMesh -count=1
```

Expected: FAIL (`parseBedMeshStatus` undefined)

- [ ] **Step 3: Implement `mesh.go`**

```go
package main

import "encoding/json"

type MeshResponse struct {
	OK      bool        `json:"ok"`
	Profile string      `json:"profile,omitempty"`
	MeshMin []float64   `json:"mesh_min,omitempty"`
	MeshMax []float64   `json:"mesh_max,omitempty"`
	Matrix  [][]float64 `json:"matrix,omitempty"`
	Error   string      `json:"error,omitempty"`
}

func parseBedMeshStatus(statusJSON []byte) MeshResponse {
	var root struct {
		BedMesh *struct {
			ProfileName  string      `json:"profile_name"`
			MeshMin      []float64   `json:"mesh_min"`
			MeshMax      []float64   `json:"mesh_max"`
			ProbedMatrix [][]float64 `json:"probed_matrix"`
		} `json:"bed_mesh"`
	}
	if err := json.Unmarshal(statusJSON, &root); err != nil || root.BedMesh == nil {
		return MeshResponse{OK: false, Error: "no_mesh"}
	}
	bm := root.BedMesh
	if bm.ProfileName == "" || len(bm.ProbedMatrix) == 0 {
		return MeshResponse{OK: false, Error: "no_mesh"}
	}
	return MeshResponse{
		OK: true, Profile: bm.ProfileName,
		MeshMin: bm.MeshMin, MeshMax: bm.MeshMax, Matrix: bm.ProbedMatrix,
	}
}
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
& "F:\github\PROG\go\bin\go.exe" test . -run TestParseBedMesh -count=1
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add webpanel/mesh.go webpanel/mesh_test.go
git commit -m "webpanel: парсер bed_mesh для GET /mesh"
```

---

### Task 2: Хендлер `GET /mesh`

**Files:**
- Modify: `webpanel/gkbridge.go` (добавить хендлер рядом с `/status`)

**Interfaces:**
- Consumes: `parseBedMeshStatus`, `klipperRequest`, `cors`, `writeJSON`
- Produces: HTTP `GET /mesh` → JSON `MeshResponse`; при dial/query error → `{ok:false, error:"..."}` (фронт покажет «нет связи с принтером»)

- [ ] **Step 1: Add helper + handler**

```go
func queryBedMesh() (json.RawMessage, error) {
	res, err := klipperRequest("objects/query", map[string]interface{}{
		"objects": map[string]interface{}{"bed_mesh": nil},
	})
	if err != nil {
		return nil, err
	}
	var r struct {
		Status json.RawMessage `json:"status"`
	}
	if json.Unmarshal(res, &r) == nil && r.Status != nil {
		return r.Status, nil
	}
	return res, nil
}

// в main(), после /status:
http.HandleFunc("/mesh", func(w http.ResponseWriter, r *http.Request) {
	if cors(w, r) {
		return
	}
	status, err := queryBedMesh()
	if err != nil {
		writeJSON(w, http.StatusOK, MeshResponse{OK: false, Error: err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, parseBedMeshStatus(status))
})
```

- [ ] **Step 2: Vet**

```powershell
cd F:\github\bedmesh\webpanel
$env:GOROOT="F:\github\PROG\go"; $env:GOOS=""; $env:GOARCH=""
& "F:\github\PROG\go\bin\go.exe" vet .
& "F:\github\PROG\go\bin\go.exe" test . -count=1
```

Expected: OK / PASS

- [ ] **Step 3: Commit**

```bash
git add webpanel/gkbridge.go
git commit -m "webpanel: эндпоинт GET /mesh"
```

---

### Task 3: Layout — левый бар + вкладка Стол

**Files:**
- Modify: `webpanel/index.html` (CSS + HTML структура body)

**Interfaces:**
- Produces DOM ids: `navPrint`, `navBed`, `panelPrint`, `panelBed`, `meshSummary`, `meshGrid`, `meshEmpty`, `btnMeshRefresh`, `meshCardHead`

- [ ] **Step 1: Replace `.layout` block with sidebar layout**

Структура (упрощённо):

```html
<header>...</header>
<div class="controls">Пауза / Стоп</div>
<div class="body-row">
  <nav class="sidebar">
    <button class="nav active" id="navPrint" type="button">🖨<br>Печать</button>
    <button class="nav" id="navBed" type="button">▦<br>Стол</button>
  </nav>
  <div class="col-main">
    <div id="panelPrint" class="grid">…текущий контент печати…</div>
    <div id="panelBed" class="card mesh-card" hidden>
      <div class="mesh-head">
        <span class="t">Карта стола</span>
        <button class="btn" id="btnMeshRefresh" type="button">Обновить</button>
      </div>
      <div id="meshSummary" class="mesh-summary"></div>
      <div id="meshGrid" class="mesh-grid"></div>
      <div id="meshEmpty" class="mesh-empty" hidden></div>
    </div>
  </div>
  <div class="col-cam" id="cameraCard">…</div>
</div>
```

CSS: как в `mockup-mesh-tab.html` (`.body-row` = `88px 1fr 1fr`, `.sidebar`, `.nav.active`).

- [ ] **Step 2: Visual check** — открыть HTML локально / через `python -m http.server`, клик Печать/Стол переключает панели; шапка и кнопки на месте.

- [ ] **Step 3: Commit**

```bash
git add webpanel/index.html
git commit -m "webpanel: левый бар Печать/Стол"
```

---

### Task 4: JS — загрузка и отрисовка mesh

**Files:**
- Modify: `webpanel/index.html` (script)

**Interfaces:**
- Consumes: `GET /mesh` → `MeshResponse`
- Produces: `loadMesh()`, `renderMesh(data)`, `colorForZ(v,zMin,zMax)`, переключение навбара

- [ ] **Step 1: Add mesh JS**

Поведение:
- `let meshLoadedOnce = false`
- клик `navBed` → показать `panelBed`, скрыть `panelPrint`; если `!meshLoadedOnce` → `loadMesh()` затем `meshLoadedOnce=true`
- клик `navPrint` → наоборот; `/mesh` не дергать
- `btnMeshRefresh` → всегда `loadMesh()`
- `loadMesh`: fetch `/mesh`; если `!ok && error==="no_mesh"` → empty «Карта стола не загружена» + «Сделайте калибровку стола в приложении BedMesh или через Klipper.»; иначе если `!ok` → «нет связи с принтером»; если ok → сетка
- Отрисовка: Y invert (последняя строка matrix сверху в DOM), soft palette stops `[[45,85,160],[140,180,220],[245,245,245],[235,170,155],[185,70,60]]`, текст `±0.xxx`, цвет текста чёрный при ratio 0.25–0.75
- Сводка: `профиль X · min · max · range`

- [ ] **Step 2: Manual logic check** — без принтера: mock JSON через временный fetch stub или DevTools; убедиться что empty/error/grid ветки работают.

- [ ] **Step 3: Commit**

```bash
git add webpanel/index.html
git commit -m "webpanel: загрузка и отрисовка карты стола"
```

---

### Task 5: Версия 1.9.0, README, сборка

**Files:**
- Modify: `webpanel/gkbridge.version` → `1.9.0`
- Modify: `webpanel/README.md` — добавить `GET /mesh`
- Modify: `webpanel/gkbridge` (бинарь)
- Delete or leave untracked: `webpanel/mockup-mesh-tab.html` (не коммитить макет)

- [ ] **Step 1: Bump version + README line**

```
GET /mesh — текущий bed_mesh (probed_matrix)
```

- [ ] **Step 2: Build**

```powershell
cd F:\github\bedmesh\webpanel
.\build.ps1
```

Expected: `OK: gkbridge v1.9.0 собран`

- [ ] **Step 3: Commit**

```bash
git add webpanel/gkbridge.version webpanel/README.md webpanel/gkbridge webpanel/index.html webpanel/gkbridge.go webpanel/mesh.go webpanel/mesh_test.go
git commit -m "webpanel: v1.9.0 — карта стола (bed mesh)"
```

---

## Spec coverage checklist

| Spec item | Task |
|---|---|
| Левый бар Печать/Стол | 3 |
| Шапка + Пауза/Стоп всегда | 3 |
| `GET /mesh` + probed_matrix | 1–2 |
| Без автополла, кнопка Обновить | 4 |
| Empty-state + подсказка | 4 |
| «нет связи с принтером» | 4 |
| `/status` без bed_mesh | 2 |
| v1.9.0 + бинарь | 5 |
