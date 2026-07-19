package main

import "encoding/json"

// MeshResponse — ответ GET /mesh.
type MeshResponse struct {
	OK      bool        `json:"ok"`
	Profile string      `json:"profile,omitempty"`
	MeshMin []float64   `json:"mesh_min,omitempty"`
	MeshMax []float64   `json:"mesh_max,omitempty"`
	Matrix  [][]float64 `json:"matrix,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// parseBedMeshStatus разбирает status из objects/query (ключ bed_mesh).
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
		OK:      true,
		Profile: bm.ProfileName,
		MeshMin: bm.MeshMin,
		MeshMax: bm.MeshMax,
		Matrix:  bm.ProbedMatrix,
	}
}
