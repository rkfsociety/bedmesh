package main

import "testing"

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
