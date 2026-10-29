package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	syncatomic "sync/atomic"
	"syscall"
	"testing"
	"time"
)

func fixture(t *testing.T, base string, i int, scope string) string {
	t.Helper()
	root := filepath.Join(base, "runs", fmt.Sprintf("creation-1000-%08x", i))
	if e := atomicFile(root, "job.json", obj{"date": "2026-10-26", "studio_plan_id": scope}); e != nil {
		t.Fatal(e)
	}
	return root
}
func atomicFile(root, name string, value interface{}) error {
	return atomic(filepath.Join(root, name), value)
}
func waitFor(t *testing.T, fn func() bool) {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		if fn() {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatal("timeout")
}

// Child fixture has a real process lifetime and holds inherited descriptors.
func TestHelper(t *testing.T) {
	switch os.Getenv("RUNNER_HELPER") {
	case "hold":
		root := os.Getenv("HELPER_ROOT")
		os.WriteFile(filepath.Join(root, "started"), []byte("yes"), 0600)
		for {
			if _, e := os.Stat(os.Getenv("HELPER_GATE")); e == nil {
				break
			}
			time.Sleep(10 * time.Millisecond)
		}
		atomicFile(root, "days/2026-10-26/day.json", obj{"status": "complete"})
		os.Exit(0)
	case "capture":
		os.Setenv("GEO_CREATION_CAPTURE_START_INTERVAL", "0") // Capacity tests isolate leases from cadence.
		args := []string{os.Getenv("HELPER_POOL"), os.Getenv("HELPER_RESOURCE"), "--", os.Args[0], "-test.run=TestHelper"}
		os.Setenv("RUNNER_HELPER", "hold")
		os.Exit(capture(args))
	}
}
func TestCaptureCadenceSharedAcrossProfiles(t *testing.T) {
	pool := t.TempDir()
	first, e := reserveCaptureStart(pool, filepath.Join(pool, "a"), 60, 100)
	if !first || e != nil {
		t.Fatal(first, e)
	}
	second, e := reserveCaptureStart(pool, filepath.Join(pool, "b"), 60, 101)
	if second || e != nil {
		t.Fatal(second, e)
	}
	wait := mustRead(filepath.Join(pool, "b.waiting.json"))
	if number(wait["next_at"]) != 160 {
		t.Fatal(wait)
	}
	next, e := reserveCaptureStart(pool, filepath.Join(pool, "b"), 60, 160)
	if !next || e != nil {
		t.Fatal(next, e)
	}
	os.WriteFile(filepath.Join(pool, "start-cadence.json"), []byte("broken"), 0600)
	if ok, e := reserveCaptureStart(pool, filepath.Join(pool, "c"), 60, 300); ok || e == nil {
		t.Fatal("unreadable state bypassed")
	}
}
func TestTenProcessesOverlapAndDrain(t *testing.T) {
	base := t.TempDir()
	gate := filepath.Join(base, "go")
	s := newScheduler(base, "unused", "unused", 10)
	for i := 0; i < 11; i++ {
		fixture(t, base, i, fmt.Sprintf("plan-%d", i))
	}
	s.launch = func(root string) (*exec.Cmd, error) {
		c := exec.Command(os.Args[0], "-test.run=TestHelper")
		c.Env = append(os.Environ(), "RUNNER_HELPER=hold", "HELPER_ROOT="+root, "HELPER_GATE="+gate)
		return c, c.Start()
	}
	if e := s.tick(false); e != nil {
		t.Fatal(e)
	}
	if len(s.active) != 10 {
		t.Fatalf("active=%d", len(s.active))
	}
	waitFor(t, func() bool {
		paths, _ := filepath.Glob(filepath.Join(base, "runs", "*", "started"))
		return len(paths) == 10
	})
	if e := s.tick(true); e != nil {
		t.Fatal(e)
	}
	if len(s.active) != 10 {
		t.Fatal("drain killed children")
	}
	os.WriteFile(gate, nil, 0600)
	waitFor(t, func() bool {
		if e := s.tick(true); e != nil {
			t.Fatal(e)
		}
		return len(s.active) == 0
	})
	paths, _ := filepath.Glob(filepath.Join(base, "runs", "*", "started"))
	if len(paths) != 10 {
		t.Fatal("drain admitted more work")
	}
	if e := s.tick(false); e != nil {
		t.Fatal(e)
	}
	waitFor(t, func() bool { s.tick(true); return len(s.active) == 0 })
	paths, _ = filepath.Glob(filepath.Join(base, "runs", "*", "started"))
	if len(paths) != 11 {
		t.Fatal("queued job did not run")
	}
}
func TestEligibilityPreservesGatesAndBadState(t *testing.T) {
	base := t.TempDir()
	root := fixture(t, base, 1, "p")
	atomicFile(root, "control.json", obj{"paused": true})
	_, ok, e := eligible(root, 100)
	if e != nil || ok {
		t.Fatal("paused admitted")
	}
	atomicFile(root, "known_preflight_retry.json", obj{"state": "waiting", "budget_pause": true, "next_at": 101})
	_, ok, _ = eligible(root, 100)
	if ok {
		t.Fatal("backoff ignored")
	}
	_, ok, _ = eligible(root, 102)
	if !ok {
		t.Fatal("due recovery lost")
	}
	atomicFile(root, "days/2026-10-26/day.json", obj{"status": "complete"})
	_, ok, _ = eligible(root, 102)
	if ok {
		t.Fatal("completed admitted")
	}
	os.WriteFile(filepath.Join(root, "job.json"), []byte("bad"), 0600)
	_, ok, e = eligible(root, 102)
	if ok || e == nil {
		t.Fatal("malformed state admitted")
	}
}
func TestFairAdmissionAndFailedLaunchIsolation(t *testing.T) {
	base := t.TempDir()
	s := newScheduler(base, "", "", 2)
	gate := filepath.Join(base, "go")
	for i := 0; i < 5; i++ {
		fixture(t, base, i, "a")
	}
	fixture(t, base, 5, "b")
	s.launch = func(root string) (*exec.Cmd, error) {
		c := exec.Command(os.Args[0], "-test.run=TestHelper")
		c.Env = append(os.Environ(), "RUNNER_HELPER=hold", "HELPER_ROOT="+root, "HELPER_GATE="+gate)
		return c, c.Start()
	}
	if e := s.tick(false); e != nil {
		t.Fatal(e)
	}
	scopes := map[string]bool{}
	for _, c := range s.active {
		scopes[c.scope] = true
	}
	if len(scopes) != 2 {
		t.Fatal("one plan monopolized slots")
	}
	os.WriteFile(gate, nil, 0600)
	waitFor(t, func() bool { s.tick(true); return len(s.active) == 0 })
	s.launch = func(string) (*exec.Cmd, error) { return nil, fmt.Errorf("missing executable") }
	if e := s.tick(false); e != nil {
		t.Fatal(e)
	}
	if len(s.active) != 0 {
		t.Fatal("failed launch counted active")
	}
}
func TestTenModelRequestsOverlapAndNoPaidRetry(t *testing.T) {
	var count int32
	entered := make(chan struct{}, 20)
	release := make(chan struct{})
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		syncatomic.AddInt32(&count, 1)
		entered <- struct{}{}
		<-release
		w.WriteHeader(503)
	}))
	defer upstream.Close()
	gateway := httptest.NewServer(modelHandler(upstream.URL, "fixture", 10, http.DefaultTransport))
	defer gateway.Close()
	var wg sync.WaitGroup
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			res, e := http.Post(gateway.URL+"/completions", "application/json", bytes.NewBufferString(`{"messages":[]}`))
			if e != nil {
				t.Error(e)
				return
			}
			io.Copy(io.Discard, res.Body)
			res.Body.Close()
			if res.StatusCode != 503 {
				t.Errorf("status %d", res.StatusCode)
			}
		}()
	}
	for i := 0; i < 10; i++ {
		select {
		case <-entered:
		case <-time.After(5 * time.Second):
			t.Fatal("model requests serialized")
		}
	}
	close(release)
	wg.Wait()
	if syncatomic.LoadInt32(&count) != 10 {
		t.Fatal("paid sends retried")
	}
}
func TestCaptureTenSlotsAndRelease(t *testing.T) {
	base := t.TempDir()
	pool := filepath.Join(base, "pool")
	gate := filepath.Join(base, "go")
	var children []*exec.Cmd
	start := func(i int) *exec.Cmd {
		root := filepath.Join(base, fmt.Sprint(i))
		os.MkdirAll(root, 0700)
		c := exec.Command(os.Args[0], "-test.run=TestHelper")
		c.Env = append(os.Environ(), "RUNNER_HELPER=capture", "HELPER_ROOT="+root, "HELPER_POOL="+pool, "HELPER_RESOURCE="+filepath.Join(root, "resource.lock"), "HELPER_GATE="+gate, "GEO_CREATION_CAPTURE_LIMIT=10", "GEO_CREATION_CAPTURE_MIN_MB=0")
		return c
	}
	defer func() {
		os.WriteFile(gate, nil, 0600)
		for _, c := range children {
			if c.ProcessState == nil {
				c.Wait()
			}
		}
	}()
	for i := 0; i < 10; i++ {
		c := start(i)
		if e := c.Start(); e != nil {
			t.Fatal(e)
		}
		children = append(children, c)
	}
	waitFor(t, func() bool { p, _ := filepath.Glob(filepath.Join(base, "*", "started")); return len(p) == 10 })
	c := start(10)
	e := c.Run()
	if x, ok := e.(*exec.ExitError); !ok || x.ExitCode() != 75 {
		t.Fatalf("11th capture should wait: %v", e)
	}
	os.WriteFile(gate, nil, 0600)
	for _, c := range children {
		if e := c.Wait(); e != nil {
			t.Fatal(e)
		}
	}
	c = start(10)
	if e := c.Run(); e != nil {
		t.Fatal("slot not released", e)
	}
	p, _ := filepath.Glob(filepath.Join(pool, "slot-*.json"))
	if len(p) != 0 {
		t.Fatal("active capture records remained")
	}
}

func TestCaptureLeaseSurvivesLauncherCrash(t *testing.T) {
	base := t.TempDir()
	pool := filepath.Join(base, "pool")
	gate := filepath.Join(base, "go")
	root := filepath.Join(base, "child")
	os.MkdirAll(root, 0700)
	start := func(resource string) *exec.Cmd {
		c := exec.Command(os.Args[0], "-test.run=TestHelper")
		c.Env = append(os.Environ(), "RUNNER_HELPER=capture", "HELPER_ROOT="+root, "HELPER_POOL="+pool, "HELPER_RESOURCE="+resource, "HELPER_GATE="+gate, "GEO_CREATION_CAPTURE_LIMIT=1", "GEO_CREATION_CAPTURE_MIN_MB=0")
		return c
	}
	first := start(filepath.Join(base, "a.lock"))
	if e := first.Start(); e != nil {
		t.Fatal(e)
	}
	defer os.WriteFile(gate, nil, 0600)
	waitFor(t, func() bool { _, e := os.Stat(filepath.Join(root, "started")); return e == nil })
	first.Process.Signal(syscall.SIGKILL)
	first.Wait()
	second := start(filepath.Join(base, "b.lock"))
	e := second.Run()
	if x, ok := e.(*exec.ExitError); !ok || x.ExitCode() != 75 {
		t.Fatalf("orphan lost its lease: %v", e)
	}
	os.WriteFile(gate, nil, 0600)
	waitFor(t, func() bool {
		f, e := lock(filepath.Join(pool, "slot-00.lock"), false)
		if e != nil {
			return false
		}
		unlock(f)
		return true
	})
	if e := start(filepath.Join(base, "b.lock")).Run(); e != nil {
		t.Fatal(e)
	}
}
