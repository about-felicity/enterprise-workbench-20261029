// Linux creation dispatcher, native model transport and on-demand capture leases.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"
)

type obj map[string]interface{}

func env(k, d string) string {
	if s := os.Getenv(k); s != "" {
		return s
	}
	return d
}
func number(v interface{}) float64 { n, _ := v.(float64); return n }
func flag(v interface{}) bool      { b, _ := v.(bool); return b }
func str(v interface{}) string     { s, _ := v.(string); return s }
func read(p string) (obj, error) {
	b, e := os.ReadFile(p)
	if os.IsNotExist(e) {
		return obj{}, nil
	}
	if e != nil {
		return nil, e
	}
	var v obj
	e = json.Unmarshal(b, &v)
	if v == nil && e == nil {
		e = errors.New("expected object")
	}
	return v, e
}
func mustRead(p string) obj {
	v, e := read(p)
	if e != nil {
		panic(e)
	}
	return v
}
func atomic(p string, v interface{}) error {
	b, e := json.Marshal(v)
	if e != nil {
		return e
	}
	if e = os.MkdirAll(filepath.Dir(p), 0700); e != nil {
		return e
	}
	f, e := os.CreateTemp(filepath.Dir(p), ".runner-*")
	if e != nil {
		return e
	}
	defer os.Remove(f.Name())
	if _, e = f.Write(b); e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e != nil {
		return e
	}
	if ce != nil {
		return ce
	}
	return os.Rename(f.Name(), p)
}
func lock(p string, wait bool) (*os.File, error) {
	if e := os.MkdirAll(filepath.Dir(p), 0700); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(p, os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	how := syscall.LOCK_EX
	if !wait {
		how |= syscall.LOCK_NB
	}
	if e = syscall.Flock(int(f.Fd()), how); e != nil {
		f.Close()
		return nil, e
	}
	return f, nil
}
func unlock(f *os.File) { syscall.Flock(int(f.Fd()), syscall.LOCK_UN); f.Close() }
func pause(root string, code int) error {
	f, e := lock(filepath.Join(root, "control.lock"), true)
	if e != nil {
		return e
	}
	defer unlock(f)
	v, e := read(filepath.Join(root, "control.json"))
	if e != nil {
		return e
	}
	v = obj{"paused": true, "revision": number(v["revision"]) + 1, "reason": "worker_process_exit", "message": "执行进程异常退出，保留原请求与进度等待核对", "paused_epoch": float64(time.Now().Unix())}
	if e = atomic(filepath.Join(root, "control.json"), v); e != nil {
		return e
	}
	return atomic(filepath.Join(root, "geo_worker.json"), obj{"at": time.Now().Unix(), "error": "worker_process_exit", "exit_code": code})
}

var terminal = map[string]bool{"complete": true, "complete_with_failures": true, "complete_with_shortfall": true, "blocked_insufficient_sources": true, "blocked_no_media_articles": true}
var jobID = regexp.MustCompile(`^creation-[0-9]+-[a-f0-9]{8}$`)
var dateID = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`)

func eligible(root string, now float64) (scope string, ok bool, err error) {
	// Malformed state fails closed for this job, never for every other job.
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("state unreadable: %v", r)
			ok = false
		}
	}()
	j := mustRead(filepath.Join(root, "job.json"))
	if len(j) == 0 {
		return "", false, nil
	}
	day := str(j["date"])
	if !dateID.MatchString(day) {
		return "", false, errors.New("invalid job date")
	}
	scope = str(j["studio_plan_id"])
	if scope == "" {
		scope = filepath.Base(root)
	}
	if number(mustRead(filepath.Join(root, "concurrency_retry.json"))["next_at"]) > now {
		return scope, false, nil
	}
	if terminal[str(mustRead(filepath.Join(root, "days", day, "day.json"))["status"])] {
		return scope, false, nil
	}
	retry := mustRead(filepath.Join(root, "known_preflight_retry.json"))
	waiting := str(retry["state"]) == "waiting"
	if waiting && number(retry["next_at"]) > now {
		return scope, false, nil
	}
	if flag(mustRead(filepath.Join(root, "control.json"))["paused"]) && !(waiting && flag(retry["budget_pause"])) {
		return scope, false, nil
	}
	if str(j["preparation"]) == "pending" && number(mustRead(filepath.Join(root, "preparation_retry.json"))["next_at"]) > now {
		return scope, false, nil
	}
	return scope, true, nil
}

type child struct {
	cmd   *exec.Cmd
	scope string
	done  chan error
}
type candidate struct{ root, name, scope string }
type scheduler struct {
	root, python, socket  string
	limit                 int
	active                map[string]*child
	last, scopeLast, next map[string]time.Time
	launch                func(string) (*exec.Cmd, error)
}

func newScheduler(root, python, socket string, limit int) *scheduler {
	s := &scheduler{root: root, python: python, socket: socket, limit: limit, active: map[string]*child{}, last: map[string]time.Time{}, scopeLast: map[string]time.Time{}, next: map[string]time.Time{}}
	s.launch = func(root string) (*exec.Cmd, error) {
		f, e := os.OpenFile(filepath.Join(root, "process-worker.log"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
		if e != nil {
			return nil, e
		}
		defer f.Close()
		c := exec.Command(s.python, "-B", "-m", "creation.worker", "--job", filepath.Base(root))
		c.Env = append(os.Environ(), "GEO_CREATION_MODEL_SOCKET="+s.socket)
		c.Stdout = f
		c.Stderr = f
		return c, c.Start()
	}
	return s
}
func (s *scheduler) tick(draining bool) error {
	now := time.Now()
	issues := map[string]string{}
	for name, c := range s.active {
		select {
		case e := <-c.done:
			delete(s.active, name)
			code := 0
			if e != nil {
				code = 1
				var x *exec.ExitError
				if errors.As(e, &x) {
					code = x.ExitCode()
				}
			}
			root := filepath.Join(s.root, "runs", name)
			if code != 0 && code != 75 {
				if e = pause(root, code); e != nil {
					return e
				}
			}
			delay := time.Duration(0)
			if code == 75 {
				delay = 2 * time.Second
			}
			v, e := read(filepath.Join(root, "geo_worker.json"))
			if e == nil {
				r, _ := v["result"].(map[string]interface{})
				if str(r["status"]) == "idle" || str(r["status"]) == "blocked_other_article_execution" {
					delay = 15 * time.Second
				}
			}
			s.next[name] = now.Add(delay)
		default:
		}
	}
	waiting := []candidate{}
	if !draining {
		paths, e := filepath.Glob(filepath.Join(s.root, "runs", "*", "job.json"))
		if e != nil {
			return e
		}
		for _, p := range paths {
			r := filepath.Dir(p)
			name := filepath.Base(r)
			if !jobID.MatchString(name) || s.active[name] != nil || now.Before(s.next[name]) {
				continue
			}
			scope, ok, e := eligible(r, float64(now.UnixNano())/1e9)
			if e != nil {
				issues[name] = "invalid_job_state"
				continue
			}
			if ok {
				waiting = append(waiting, candidate{r, name, scope})
			}
		}
		scopes := map[string]int{}
		for _, c := range s.active {
			scopes[c.scope]++
		}
		for len(waiting) > 0 && len(s.active) < s.limit {
			sort.Slice(waiting, func(i, j int) bool {
				a, b := waiting[i], waiting[j]
				if scopes[a.scope] != scopes[b.scope] {
					return scopes[a.scope] < scopes[b.scope]
				}
				if !s.scopeLast[a.scope].Equal(s.scopeLast[b.scope]) {
					return s.scopeLast[a.scope].Before(s.scopeLast[b.scope])
				}
				if !s.last[a.name].Equal(s.last[b.name]) {
					return s.last[a.name].Before(s.last[b.name])
				}
				return a.name < b.name
			})
			v := waiting[0]
			waiting = waiting[1:]
			cmd, e := s.launch(v.root)
			if e != nil {
				issues[v.name] = "process_start_failed"
				s.next[v.name] = now.Add(15 * time.Second)
				continue
			}
			c := &child{cmd: cmd, scope: v.scope, done: make(chan error, 1)}
			s.active[v.name] = c
			go func() { c.done <- c.cmd.Wait() }()
			s.last[v.name] = time.Now()
			s.scopeLast[v.scope] = s.last[v.name]
			scopes[v.scope]++
		}
	}
	active := []obj{}
	for name, c := range s.active {
		active = append(active, obj{"job_id": name, "pid": c.cmd.Process.Pid, "plan_id": c.scope})
	}
	status := "running"
	if draining {
		status = "draining"
	}
	return atomic(filepath.Join(s.root, "worker_health.json"), obj{"at": float64(now.UnixNano()) / 1e9, "status": status, "mode": "go_dynamic", "max_parallel_jobs": s.limit, "active_jobs": active, "queued_jobs": len(waiting), "issues": issues, "model_transport": "go", "capture_limit": 10})
}

// Model IO is native Go with a shared connection pool, bounded concurrency and
// no retries or redirects for paid POSTs. Durable intent and budgets remain in
// the existing engine before this transport is entered.
func modelHandler(upstream, key string, limit int, transport http.RoundTripper) http.Handler {
	gate := make(chan struct{}, limit)
	client := &http.Client{Transport: transport, Timeout: 310 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := ""
		if r.Method == "GET" && r.URL.Path == "/balance" {
			path = "/user/balance"
		}
		if r.Method == "POST" && r.URL.Path == "/completions" {
			path = "/chat/completions"
		}
		if path == "" {
			http.Error(w, "unsupported request", 404)
			return
		}
		select {
		case gate <- struct{}{}:
			defer func() { <-gate }()
		case <-r.Context().Done():
			return
		}
		var body io.Reader
		if r.Method == "POST" {
			b, e := io.ReadAll(http.MaxBytesReader(w, r.Body, 8<<20))
			if e != nil {
				http.Error(w, "request too large", 413)
				return
			}
			if !json.Valid(b) {
				http.Error(w, "invalid JSON", 400)
				return
			}
			body = strings.NewReader(string(b))
		}
		req, e := http.NewRequestWithContext(r.Context(), r.Method, upstream+path, body)
		if e != nil {
			http.Error(w, "request failed", 502)
			return
		}
		req.GetBody = nil // Never make a paid POST replayable on a reused connection.
		req.Header.Set("Authorization", "Bearer "+key)
		req.Header.Set("Content-Type", "application/json")
		res, e := client.Do(req)
		if e != nil {
			http.Error(w, "upstream delivery unknown", 502)
			return
		}
		defer res.Body.Close()
		b, e := io.ReadAll(io.LimitReader(res.Body, (16<<20)+1))
		if e != nil || len(b) > 16<<20 {
			http.Error(w, "upstream response incomplete", 502)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(res.StatusCode)
		w.Write(b)
	})
}
func serve() error {
	root := env("GEO_CREATION_ROOT", "/opt/monitor/geo-content/runtime")
	limit, e := strconv.Atoi(env("GEO_CREATION_CONCURRENCY", "10"))
	if e != nil || limit < 1 || limit > 32 {
		return errors.New("concurrency must be 1..32")
	}
	owner, e := lock(filepath.Join(root, "worker.lock"), false)
	if e != nil {
		return e
	}
	defer unlock(owner)
	socket := filepath.Join(root, "model.sock")
	key, e := os.ReadFile(env("GEO_CREATION_KEY_FILE", "/home/user/geo-editorial/secrets/deepseek.key"))
	if e != nil {
		return e
	}
	if !regexp.MustCompile(`^sk-[A-Za-z0-9_-]{20,}$`).MatchString(strings.TrimSpace(string(key))) {
		return errors.New("invalid key file")
	}
	if st, e := os.Lstat(socket); e == nil {
		if st.Mode()&os.ModeSocket == 0 {
			return errors.New("socket path is not a socket")
		}
		if e = os.Remove(socket); e != nil {
			return e
		}
	}
	ln, e := net.Listen("unix", socket)
	if e != nil {
		return e
	}
	defer os.Remove(socket)
	defer ln.Close()
	if e = os.Chmod(socket, 0600); e != nil {
		return e
	}
	transport := &http.Transport{Proxy: http.ProxyFromEnvironment, DialContext: (&net.Dialer{Timeout: 15 * time.Second, KeepAlive: 30 * time.Second}).DialContext, MaxIdleConns: 64, MaxIdleConnsPerHost: limit, MaxConnsPerHost: limit, TLSHandshakeTimeout: 15 * time.Second, IdleConnTimeout: 90 * time.Second}
	server := &http.Server{Handler: modelHandler("https://api.deepseek.com", strings.TrimSpace(string(key)), limit, transport), ReadHeaderTimeout: 10 * time.Second, ReadTimeout: 30 * time.Second, WriteTimeout: 330 * time.Second}
	serverDone := make(chan error, 1)
	go func() { serverDone <- server.Serve(ln) }()
	s := newScheduler(root, env("GEO_CREATION_PYTHON", "/home/user/geo-editorial/venv/bin/python"), socket, limit)
	signals := make(chan os.Signal, 2)
	signal.Notify(signals, syscall.SIGTERM, syscall.SIGINT)
	defer signal.Stop(signals)
	draining := false
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-signals:
			draining = true
		case e := <-serverDone:
			if e != http.ErrServerClosed {
				return e
			}
		case <-ticker.C:
		}
		hold, e := read(filepath.Join(root, "worker_drain.json"))
		if e != nil {
			hold = obj{"enabled": true}
		}
		if e = s.tick(draining || flag(hold["enabled"])); e != nil {
			return e
		}
		if draining && len(s.active) == 0 {
			ctx, cancel := context.WithTimeout(context.Background(), 330*time.Second)
			defer cancel()
			return server.Shutdown(ctx)
		}
	}
}

// A lease is held by the Go launcher and inherited by its child. If a launcher
// is killed, a surviving browser adapter still owns its slot and profile lock.
func availableMB() int64 {
	b, e := os.ReadFile("/proc/meminfo")
	if e != nil {
		return 0
	}
	for _, line := range strings.Split(string(b), "\n") {
		f := strings.Fields(line)
		if len(f) > 1 && f[0] == "MemAvailable:" {
			n, _ := strconv.ParseInt(f[1], 10, 64)
			return n / 1024
		}
	}
	return 0
}

// Called under admission.lock. Browser concurrency and aggregate request cadence
// are separate limits: independent profiles must not multiply the site's rate.
func reserveCaptureStart(pool, resource string, interval, now float64) (bool, error) {
	if interval == 0 {
		return true, nil
	}
	path := filepath.Join(pool, "start-cadence.json")
	previous, err := read(path)
	if err != nil {
		return false, err
	}
	if len(previous) > 0 {
		last, ok := previous["started_at"].(float64)
		if !ok || last < 0 {
			return false, errors.New("invalid capture cadence state")
		}
		if now < last+interval {
			return false, atomic(resource+".waiting.json", obj{"kind": "site_cadence", "at": now, "next_at": last + interval})
		}
	}
	return true, atomic(path, obj{"started_at": now, "resource": resource, "interval_seconds": interval})
}
func capture(args []string) int {
	if len(args) < 4 || args[2] != "--" {
		fmt.Fprintln(os.Stderr, "capture POOL RESOURCE_LOCK -- COMMAND...")
		return 2
	}
	pool, resource := args[0], args[1]
	limit, e := strconv.Atoi(env("GEO_CREATION_CAPTURE_LIMIT", "10"))
	if e != nil || limit < 1 || limit > 32 {
		return 2
	}
	min, e := strconv.ParseInt(env("GEO_CREATION_CAPTURE_MIN_MB", "1200"), 10, 64)
	if e != nil || min < 0 {
		return 2
	}
	interval, e := strconv.ParseFloat(env("GEO_CREATION_CAPTURE_START_INTERVAL", "60"), 64)
	if e != nil || interval < 0 || interval > 900 {
		return 2
	}
	admission, e := lock(filepath.Join(pool, "admission.lock"), true)
	if e != nil {
		return 75
	}
	defer func() {
		if admission != nil {
			unlock(admission)
		}
	}()
	// Reserve startup headroom while recently launched browsers are still
	// allocating memory, so simultaneous arrivals cannot all see the same RAM.
	pending := int64(0)
	if min > 0 {
		paths, _ := filepath.Glob(filepath.Join(pool, "slot-*.json"))
		for _, p := range paths {
			v, err := read(p)
			if err == nil && time.Now().Unix()-int64(number(v["started_at"])) < 30 && syscall.Kill(int(number(v["pid"])), 0) == nil {
				pending += 256
			}
		}
	}
	if availableMB()-pending < min {
		atomic(resource+".waiting.json", obj{"kind": "memory", "at": time.Now().Unix()})
		fmt.Fprintln(os.Stderr, "waiting_memory_capacity")
		return 75
	}
	r, e := lock(resource, false)
	if e != nil {
		return 75
	}
	defer unlock(r)
	var slot *os.File
	index := -1
	for i := 0; i < limit; i++ {
		f, e := lock(filepath.Join(pool, fmt.Sprintf("slot-%02d.lock", i)), false)
		if e == nil {
			slot = f
			index = i
			break
		}
	}
	if slot == nil {
		atomic(resource+".waiting.json", obj{"kind": "slots", "at": time.Now().Unix()})
		fmt.Fprintln(os.Stderr, "waiting_capture_slot")
		return 75
	}
	defer unlock(slot)
	allowed, err := reserveCaptureStart(pool, resource, interval, float64(time.Now().UnixNano())/1e9)
	if err != nil {
		fmt.Fprintln(os.Stderr, "capture_cadence_state_error")
		return 75
	}
	if !allowed {
		fmt.Fprintln(os.Stderr, "waiting_site_cadence")
		return 75
	}
	cmd := exec.Command(args[3], args[4:]...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	cmd.ExtraFiles = []*os.File{r, slot}
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	if e = cmd.Start(); e != nil {
		fmt.Fprintln(os.Stderr, "capture_start_failed")
		return 1
	}
	note := filepath.Join(pool, fmt.Sprintf("slot-%02d.json", index))
	if e = atomic(note, obj{"pid": cmd.Process.Pid, "launcher_pid": os.Getpid(), "resource": resource, "started_at": time.Now().Unix()}); e != nil {
		log.Print(e)
	}
	unlock(admission)
	admission = nil
	os.Remove(resource + ".waiting.json")
	defer os.Remove(note)
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	signals := make(chan os.Signal, 2)
	signal.Notify(signals, syscall.SIGTERM, syscall.SIGINT)
	defer signal.Stop(signals)
	for {
		select {
		case sig := <-signals:
			syscall.Kill(-cmd.Process.Pid, sig.(syscall.Signal))
		case e = <-done:
			if e == nil {
				return 0
			}
			var x *exec.ExitError
			if errors.As(e, &x) {
				return x.ExitCode()
			}
			return 1
		}
	}
}
func main() {
	if len(os.Args) > 1 && os.Args[1] == "capture" {
		os.Exit(capture(os.Args[2:]))
	}
	if len(os.Args) != 2 || os.Args[1] != "serve" {
		log.Fatal("use serve or capture")
	}
	if e := serve(); e != nil {
		log.Fatal(e)
	}
}
