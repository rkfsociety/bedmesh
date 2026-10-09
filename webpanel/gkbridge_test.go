package main

import "testing"

func TestGkbridgeReleaseURL(t *testing.T) {
	url, err := gkbridgeReleaseURL("1.9.6")
	if err != nil {
		t.Fatalf("gkbridgeReleaseURL returned an error: %v", err)
	}
	want := "https://github.com/rkfsociety/bedmesh/releases/download/v1.9.6-gkbridge/gkbridge"
	if url != want {
		t.Fatalf("gkbridgeReleaseURL = %q, want %q", url, want)
	}
}

func TestGkbridgeReleaseURLRejectsInvalidVersion(t *testing.T) {
	for _, version := range []string{"", "1.9", "1.9.6/../../win", "v1.9.6", "1.9.6-rc1"} {
		if _, err := gkbridgeReleaseURL(version); err == nil {
			t.Errorf("gkbridgeReleaseURL(%q) accepted an invalid version", version)
		}
	}
}
