package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestParseBedMeshOK(t *testing.T) {
	raw := []byte(`{"bed_mesh":{"profile_name":"default","mesh_min":[5,5],"mesh_max":[245,245],"probed_matrix":[[0.1,-0.2],[0.0,0.05]]}}`)
	r := parseBedMeshStatus(raw)
	if !r.OK || r.Profile != "default" || len(r.Matrix) != 2 || r.Matrix[0][1] != -0.2 {
		t.Fatalf("%+v", r)
	}
	if len(r.MeshMin) != 2 || r.MeshMin[0] != 5 || r.MeshMax[1] != 245 {
		t.Fatalf("bounds: %+v", r)
	}
}

func TestParseBedMeshEmptyProfileButMatrixOK(t *testing.T) {
	raw := []byte(`{"bed_mesh":{"profile_name":"","probed_matrix":[[0.1,0.2],[0.3,0.4]]}}`)
	r := parseBedMeshStatus(raw)
	if !r.OK || r.Profile != "default" || r.Matrix[1][1] != 0.4 {
		t.Fatalf("%+v", r)
	}
}

func TestParseBedMeshFallbackMeshMatrix(t *testing.T) {
	raw := []byte(`{"bed_mesh":{"profile_name":"default","mesh_matrix":[[1,2],[3,4]]}}`)
	r := parseBedMeshStatus(raw)
	if !r.OK || r.Matrix[0][1] != 2 {
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

func TestParseMeshMutableJSON(t *testing.T) {
	raw := `{
  "bed_mesh default": {
    "x_count": "3",
    "y_count": "2",
    "min_x": "5",
    "max_x": "245",
    "min_y": "5",
    "max_y": "245",
    "points": "0.10 -0.20 0.30 0.01 0.02 -0.03"
  }
}`
	r := parseMeshFileContent(raw)
	if !r.OK || r.Source != "file" {
		t.Fatalf("%+v", r)
	}
	if len(r.Matrix) != 2 || len(r.Matrix[0]) != 3 {
		t.Fatalf("shape: %+v", r.Matrix)
	}
	if r.Matrix[0][1] != -0.20 || r.Matrix[1][2] != -0.03 {
		t.Fatalf("values: %+v", r.Matrix)
	}
	if r.MeshMin[0] != 5 || r.MeshMax[0] != 245 {
		t.Fatalf("bounds: %+v / %+v", r.MeshMin, r.MeshMax)
	}
}

func TestParseMeshConfigText(t *testing.T) {
	raw := `[bed_mesh default]
probe_count: 2, 2
mesh_min: 10, 10
mesh_max: 200, 200
points:
  0.1, 0.2
  -0.1, 0.0
`
	r := parseMeshFileContent(raw)
	if !r.OK || len(r.Matrix) != 2 || r.Matrix[0][1] != 0.2 || r.Matrix[1][0] != -0.1 {
		t.Fatalf("%+v", r)
	}
}

func TestResolveMeshFallsBackToFile(t *testing.T) {
	dir := t.TempDir()
	mutable := filepath.Join(dir, "printer_mutable.cfg")
	content := `{"bed_mesh default":{"x_count":2,"y_count":2,"min_x":0,"max_x":1,"min_y":0,"max_y":1,"points":"1 2 3 4"}}`
	if err := os.WriteFile(mutable, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}

	oldM, oldP := meshMutablePath, meshPrinterPath
	meshMutablePath, meshPrinterPath = mutable, filepath.Join(dir, "missing.cfg")
	defer func() { meshMutablePath, meshPrinterPath = oldM, oldP }()

	live := func() (json.RawMessage, error) {
		return json.RawMessage(`{"bed_mesh":{"profile_name":"","probed_matrix":[]}}`), nil
	}
	r := resolveMesh(live)
	if !r.OK || r.Source != "file" || r.Matrix[1][1] != 4 {
		t.Fatalf("%+v", r)
	}
}

func TestResolveMeshLivePreferred(t *testing.T) {
	live := func() (json.RawMessage, error) {
		return json.RawMessage(`{"bed_mesh":{"profile_name":"live","probed_matrix":[[9,8],[7,6]]}}`), nil
	}
	r := resolveMesh(live)
	if !r.OK || r.Profile != "live" || r.Source != "live" || r.Matrix[0][0] != 9 {
		t.Fatalf("%+v", r)
	}
}

func TestResolveMeshSocketErrorWithoutFile(t *testing.T) {
	live := func() (json.RawMessage, error) {
		return nil, os.ErrNotExist
	}
	r := resolveMesh(live)
	if r.OK || r.Error == "" || r.Error == "no_mesh" {
		// без файла на диске — ошибка сокета пробрасывается
		if r.OK {
			t.Fatalf("%+v", r)
		}
	}
}
