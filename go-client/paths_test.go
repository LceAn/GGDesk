package main

import (
	"path/filepath"
	"testing"
)

func TestParseTargetExtensionsNormalizesValues(t *testing.T) {
	got := parseTargetExtensions(" .EXE, , .lnk ,EXE ")
	want := []string{".exe", ".lnk", "exe"}
	if len(got) != len(want) {
		t.Fatalf("got %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got %v, want %v", got, want)
		}
	}
}

func TestSortedUniqueIsCaseInsensitive(t *testing.T) {
	got := sortedUnique([]string{" Beta ", "alpha", "ALPHA", "", "beta"})
	want := []string{"alpha", "Beta"}
	if len(got) != len(want) {
		t.Fatalf("got %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("got %v, want %v", got, want)
		}
	}
}

func TestNormalizeTargetAndFilesystemDetection(t *testing.T) {
	if got, want := normalizeTarget(`C:\\Apps\\Demo.exe`), filepath.Clean(`c:\\apps\\demo.exe`); got != want {
		t.Fatalf("normalizeTarget() = %q, want %q", got, want)
	}
	if !looksLikeFilesystemPath(`C:\\Apps\\Demo.exe`) {
		t.Fatal("Windows path should be recognized")
	}
	if looksLikeFilesystemPath("shell:AppsFolder\\Vendor.App") {
		t.Fatal("UWP shell target should not be treated as a filesystem path")
	}
}
