package main

import (
	"encoding/json"
	"os"
	"regexp"
	"strconv"
	"strings"
)

// Пути на принтере Kobra S1 / GoKlipper — как в desktop/android приложении.
// var (не const), чтобы тесты могли подменить.
var (
	meshMutablePath = "/userdata/app/gk/printer_mutable.cfg"
	meshPrinterPath = "/userdata/app/gk/printer.cfg"
)

// MeshResponse — ответ GET /mesh.
type MeshResponse struct {
	OK      bool        `json:"ok"`
	Profile string      `json:"profile,omitempty"`
	MeshMin []float64   `json:"mesh_min,omitempty"`
	MeshMax []float64   `json:"mesh_max,omitempty"`
	Matrix  [][]float64 `json:"matrix,omitempty"`
	Error   string      `json:"error,omitempty"`
	Source  string      `json:"source,omitempty"` // "live" | "file"
}

func meshNoMesh() MeshResponse { return MeshResponse{OK: false, Error: "no_mesh"} }

// parseBedMeshStatus разбирает status из objects/query (ключ bed_mesh).
func parseBedMeshStatus(statusJSON []byte) MeshResponse {
	var root map[string]json.RawMessage
	if err := json.Unmarshal(statusJSON, &root); err != nil {
		return meshNoMesh()
	}
	raw, ok := root["bed_mesh"]
	if !ok || len(raw) == 0 || string(raw) == "null" {
		return meshNoMesh()
	}
	var bm map[string]json.RawMessage
	if err := json.Unmarshal(raw, &bm); err != nil {
		return meshNoMesh()
	}

	profile, _ := jsonString(bm["profile_name"])
	matrix := parseFloatMatrix(bm["probed_matrix"])
	if len(matrix) == 0 {
		matrix = parseFloatMatrix(bm["mesh_matrix"])
	}
	if len(matrix) == 0 {
		return meshNoMesh()
	}
	if profile == "" {
		profile = "default"
	}
	min := parseFloatSlice(bm["mesh_min"])
	max := parseFloatSlice(bm["mesh_max"])
	return MeshResponse{
		OK: true, Profile: profile, MeshMin: min, MeshMax: max, Matrix: matrix, Source: "live",
	}
}

// parseMeshFileContent — JSON (printer_mutable) или текстовый cfg, как в приложении.
func parseMeshFileContent(text string) MeshResponse {
	trimmed := strings.TrimSpace(text)
	if trimmed == "" {
		return meshNoMesh()
	}
	if strings.HasPrefix(trimmed, "{") {
		if r := parseMeshMutableJSON([]byte(trimmed)); r.OK {
			return r
		}
	}
	return parseMeshConfigText(trimmed)
}

func parseMeshMutableJSON(data []byte) MeshResponse {
	var root map[string]json.RawMessage
	if err := json.Unmarshal(data, &root); err != nil {
		return meshNoMesh()
	}
	raw, ok := root["bed_mesh default"]
	if !ok {
		// иногда ключ без пробела / другое имя профиля
		for k, v := range root {
			if strings.HasPrefix(k, "bed_mesh") {
				raw, ok = v, true
				break
			}
		}
	}
	if !ok {
		return meshNoMesh()
	}
	var mesh map[string]json.RawMessage
	if err := json.Unmarshal(raw, &mesh); err != nil {
		return meshNoMesh()
	}

	xCount := int(jsonFlexibleFloat(mesh["x_count"]))
	yCount := int(jsonFlexibleFloat(mesh["y_count"]))
	if xCount <= 0 || yCount <= 0 {
		return meshNoMesh()
	}
	minX := jsonFlexibleFloat(mesh["min_x"])
	maxX := jsonFlexibleFloat(mesh["max_x"])
	minY := jsonFlexibleFloat(mesh["min_y"])
	maxY := jsonFlexibleFloat(mesh["max_y"])

	pointsRaw, _ := jsonString(mesh["points"])
	if pointsRaw == "" {
		// иногда points — массив
		if flat := parseFloatSlice(mesh["points"]); len(flat) == xCount*yCount {
			return meshFromFlat("default", flat, xCount, yCount, minX, maxX, minY, maxY, "file")
		}
		return meshNoMesh()
	}
	flat := splitFloats(pointsRaw)
	if len(flat) != xCount*yCount {
		return meshNoMesh()
	}
	return meshFromFlat("default", flat, xCount, yCount, minX, maxX, minY, maxY, "file")
}

var (
	reCfgKey   = regexp.MustCompile(`(?i)^([A-Za-z_][A-Za-z0-9_]*)\s*[:=]`)
	reSplitNum = regexp.MustCompile(`[,\s]+`)
)

func parseMeshConfigText(text string) MeshResponse {
	lines := strings.Split(text, "\n")
	var section []string
	in := false
	for _, line := range lines {
		st := strings.TrimSpace(line)
		if strings.HasPrefix(st, "[") && strings.Contains(st, "bed_mesh") {
			in = true
			section = section[:0]
			continue
		}
		if in {
			if strings.HasPrefix(st, "[") {
				break
			}
			section = append(section, line)
		}
	}
	if len(section) == 0 {
		return meshNoMesh()
	}

	get := func(key string) string {
		for _, l := range section {
			l = strings.Split(l, "#")[0]
			l = strings.TrimSpace(l)
			lower := strings.ToLower(l)
			prefColon := strings.ToLower(key) + ":"
			prefEq := strings.ToLower(key) + "="
			prefEqSp := strings.ToLower(key) + " ="
			if strings.HasPrefix(lower, prefColon) {
				return strings.TrimSpace(l[len(key)+1:])
			}
			if strings.HasPrefix(lower, prefEq) {
				return strings.TrimSpace(strings.SplitN(l, "=", 2)[1])
			}
			if strings.HasPrefix(lower, prefEqSp) {
				return strings.TrimSpace(strings.SplitN(l, "=", 2)[1])
			}
		}
		return ""
	}

	xCount, yCount := 0, 0
	if p := splitFloats(get("probe_count")); len(p) == 2 {
		xCount, yCount = int(p[0]), int(p[1])
	}
	if xCount <= 0 || yCount <= 0 {
		xCount = int(parseFloatOr(get("x_count"), 0))
		yCount = int(parseFloatOr(get("y_count"), 0))
	}
	if xCount <= 0 || yCount <= 0 {
		return meshNoMesh()
	}

	var minX, maxX, minY, maxY float64
	if mn := splitFloats(get("mesh_min")); len(mn) == 2 {
		minX, minY = mn[0], mn[1]
	} else {
		minX = parseFloatOr(get("min_x"), 0)
		minY = parseFloatOr(get("min_y"), 0)
	}
	if mx := splitFloats(get("mesh_max")); len(mx) == 2 {
		maxX, maxY = mx[0], mx[1]
	} else {
		maxX = parseFloatOr(get("max_x"), 0)
		maxY = parseFloatOr(get("max_y"), 0)
	}

	var pts []string
	capture := false
	for _, raw := range section {
		noComment := strings.Split(raw, "#")[0]
		st := strings.TrimSpace(noComment)
		lower := strings.ToLower(st)
		if strings.HasPrefix(lower, "points") && (strings.Contains(st, ":") || strings.Contains(st, "=")) {
			capture = true
			var after string
			if i := strings.Index(st, ":"); i >= 0 {
				after = strings.TrimSpace(st[i+1:])
			} else if i := strings.Index(st, "="); i >= 0 {
				after = strings.TrimSpace(st[i+1:])
			}
			if after != "" {
				pts = append(pts, after)
			}
			continue
		}
		if capture {
			if strings.HasPrefix(st, "[") {
				break
			}
			if reCfgKey.MatchString(st) {
				break
			}
			if st != "" {
				pts = append(pts, st)
			}
		}
	}
	if len(pts) == 0 {
		return meshNoMesh()
	}

	var rows [][]float64
	for _, line := range pts {
		cleaned := strings.Trim(strings.TrimSpace(line), "[]()")
		parts := reSplitNum.Split(cleaned, -1)
		var row []float64
		for _, p := range parts {
			if p == "" {
				continue
			}
			v, err := strconv.ParseFloat(p, 64)
			if err != nil {
				row = nil
				break
			}
			row = append(row, v)
		}
		if len(row) > 0 {
			rows = append(rows, row)
		}
	}

	var matrix [][]float64
	if len(rows) == yCount {
		ok := true
		for _, r := range rows {
			if len(r) != xCount {
				ok = false
				break
			}
		}
		if ok {
			matrix = rows
		}
	}
	if matrix == nil {
		var flat []float64
		for _, r := range rows {
			flat = append(flat, r...)
		}
		if len(flat) != xCount*yCount {
			return meshNoMesh()
		}
		return meshFromFlat("default", flat, xCount, yCount, minX, maxX, minY, maxY, "file")
	}
	return MeshResponse{
		OK: true, Profile: "default",
		MeshMin: []float64{minX, minY}, MeshMax: []float64{maxX, maxY},
		Matrix: matrix, Source: "file",
	}
}

func meshFromFlat(profile string, flat []float64, xCount, yCount int, minX, maxX, minY, maxY float64, source string) MeshResponse {
	matrix := make([][]float64, yCount)
	for i := 0; i < yCount; i++ {
		matrix[i] = flat[i*xCount : (i+1)*xCount]
	}
	return MeshResponse{
		OK: true, Profile: profile,
		MeshMin: []float64{minX, minY}, MeshMax: []float64{maxX, maxY},
		Matrix: matrix, Source: source,
	}
}

func loadMeshFromDisk() MeshResponse {
	for _, path := range []string{meshMutablePath, meshPrinterPath} {
		b, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		r := parseMeshFileContent(string(b))
		if r.OK {
			r.Source = "file"
			return r
		}
	}
	return meshNoMesh()
}

// resolveMesh: живой bed_mesh, иначе файл на диске (как desktop app).
func resolveMesh(queryLive func() (json.RawMessage, error)) MeshResponse {
	var liveErr error
	if status, err := queryLive(); err == nil {
		r := parseBedMeshStatus(status)
		if r.OK {
			return r
		}
	} else {
		liveErr = err
	}
	if r := loadMeshFromDisk(); r.OK {
		return r
	}
	if liveErr != nil {
		return MeshResponse{OK: false, Error: liveErr.Error()}
	}
	return meshNoMesh()
}

// ── helpers ──────────────────────────────────────────────────────────────

func jsonString(raw json.RawMessage) (string, bool) {
	if len(raw) == 0 {
		return "", false
	}
	var s string
	if err := json.Unmarshal(raw, &s); err == nil {
		return s, true
	}
	return strings.Trim(string(raw), `"`), true
}

func jsonFlexibleFloat(raw json.RawMessage) float64 {
	if len(raw) == 0 {
		return 0
	}
	var f float64
	if err := json.Unmarshal(raw, &f); err == nil {
		return f
	}
	var s string
	if err := json.Unmarshal(raw, &s); err == nil {
		v, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
		return v
	}
	return 0
}

func parseFloatOr(s string, def float64) float64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return def
	}
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return def
	}
	return v
}

func splitFloats(s string) []float64 {
	s = strings.Trim(strings.TrimSpace(s), "[]()")
	if s == "" {
		return nil
	}
	parts := reSplitNum.Split(s, -1)
	out := make([]float64, 0, len(parts))
	for _, p := range parts {
		if p == "" {
			continue
		}
		v, err := strconv.ParseFloat(p, 64)
		if err != nil {
			return nil
		}
		out = append(out, v)
	}
	return out
}

func parseFloatSlice(raw json.RawMessage) []float64 {
	if len(raw) == 0 {
		return nil
	}
	var nums []float64
	if err := json.Unmarshal(raw, &nums); err == nil {
		return nums
	}
	var strs []string
	if err := json.Unmarshal(raw, &strs); err == nil {
		out := make([]float64, 0, len(strs))
		for _, s := range strs {
			v, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
			if err != nil {
				return nil
			}
			out = append(out, v)
		}
		return out
	}
	var s string
	if err := json.Unmarshal(raw, &s); err == nil {
		return splitFloats(s)
	}
	return nil
}

func parseFloatMatrix(raw json.RawMessage) [][]float64 {
	if len(raw) == 0 {
		return nil
	}
	var m [][]float64
	if err := json.Unmarshal(raw, &m); err == nil && len(m) > 0 {
		return m
	}
	var any [][]json.RawMessage
	if err := json.Unmarshal(raw, &any); err == nil && len(any) > 0 {
		out := make([][]float64, 0, len(any))
		for _, row := range any {
			r := make([]float64, 0, len(row))
			for _, cell := range row {
				r = append(r, jsonFlexibleFloat(cell))
			}
			out = append(out, r)
		}
		return out
	}
	return nil
}
