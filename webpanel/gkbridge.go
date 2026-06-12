// gkbridge — крошечный мост между Klipper-сокетом GoKlipper (gklib) и HTTP.
// Читает /tmp/unix_uds1 (урезанный Klipper API, JSON-кадры с терминатором 0x03),
// отдаёт чистый JSON по HTTP с CORS, чтобы статичная веб-панель могла опрашивать
// принтер прямо из браузера, а также управлять печатью (пауза/продолжить/стоп,
// установка температур) через отправку gcode в тот же сокет.
//
// Сборка под принтер (armv7 Linux):
//   GOOS=linux GOARCH=arm GOARM=7 go build -ldflags="-s -w" -o gkbridge gkbridge.go
//
// Запуск на принтере:
//   ./gkbridge &           (по умолчанию слушает :8088, сокет /tmp/unix_uds1)
//   ./gkbridge -addr :9000 -socket /tmp/unix_uds1
package main

import (
	"bytes"
	"crypto/tls"
	_ "embed"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

//go:embed index.html
var indexHTML []byte

//go:embed gkbridge.version
var versionRaw []byte

// version — собственная версия веб-панели (из файла gkbridge.version).
func version() string { return strings.TrimSpace(string(versionRaw)) }

// repoRawBase — где лежат свежий бинарник и файл версии (raw GitHub).
const repoRawBase = "https://raw.githubusercontent.com/rkfsociety/bedmesh/main/webpanel"

const etx = 0x03 // терминатор кадра Klipper API

// httpClient для запросов к GitHub. На принтере может не быть CA-бандла, поэтому
// проверку сертификата отключаем (качаем свой же бинарник по фиксированному URL).
var httpClient = &http.Client{
	Timeout:   90 * time.Second,
	Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}},
}

// fetchLatestVersion возвращает версию из репозитория (raw).
func fetchLatestVersion() (string, error) {
	resp, err := httpClient.Get(repoRawBase + "/gkbridge.version")
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	b, err := io.ReadAll(io.LimitReader(resp.Body, 64))
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(b)), nil
}

// applyUpdate скачивает свежий бинарник, заменяет текущий и перезапускает процесс.
func applyUpdate() error {
	exe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("executable: %w", err)
	}
	exe, _ = filepath.EvalSymlinks(exe)

	resp, err := httpClient.Get(repoRawBase + "/gkbridge")
	if err != nil {
		return fmt.Errorf("download: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download HTTP %d", resp.StatusCode)
	}

	tmp := exe + ".new"
	out, err := os.OpenFile(tmp, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o755)
	if err != nil {
		return fmt.Errorf("create tmp: %w", err)
	}
	n, err := io.Copy(out, resp.Body)
	out.Close()
	if err != nil {
		os.Remove(tmp)
		return fmt.Errorf("write tmp: %w", err)
	}
	if n < 1024*1024 { // бинарник ~5.5 МБ; защита от усечённой/битой загрузки
		os.Remove(tmp)
		return fmt.Errorf("downloaded too small: %d bytes", n)
	}

	// Заменяем файл (running-процесс держит старый inode — это нормально для Linux).
	if err := os.Rename(tmp, exe); err != nil {
		os.Remove(tmp)
		return fmt.Errorf("replace: %w", err)
	}

	// Перезапуск: даём текущему процессу выйти (освободить порт), затем стартуем новый.
	cmd := exec.Command("sh", "-c", fmt.Sprintf("sleep 1; nohup '%s' >/tmp/gkbridge.out 2>&1 &", exe))
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("restart: %w", err)
	}
	go func() { time.Sleep(400 * time.Millisecond); os.Exit(0) }()
	return nil
}

// объекты, которые запрашиваем у gklib
var queryObjects = map[string]interface{}{
	"print_stats":    nil,
	"virtual_sdcard": nil,
	"extruder":       nil,
	"heater_bed":     nil,
	"toolhead":       nil,
	"gcode_move":     nil,
	"fan":            nil,
	"filament_hub":   nil,
}

var (
	socketPath = flag.String("socket", "/tmp/unix_uds1", "путь к unix-сокету gklib")
	listenAddr = flag.String("addr", ":8088", "адрес HTTP-сервера")
)

// klipperRequest открывает свежее соединение с сокетом, шлёт один запрос
// (method+params) и возвращает поле result ответа с нашим id (или ошибку).
func klipperRequest(method string, params interface{}) (json.RawMessage, error) {
	conn, err := net.DialTimeout("unix", *socketPath, 3*time.Second)
	if err != nil {
		return nil, fmt.Errorf("dial: %w", err)
	}
	defer conn.Close()

	req := map[string]interface{}{"method": method, "id": 1}
	if params != nil {
		req["params"] = params
	}
	payload, _ := json.Marshal(req)
	payload = append(payload, etx)

	conn.SetDeadline(time.Now().Add(6 * time.Second))
	if _, err := conn.Write(payload); err != nil {
		return nil, fmt.Errorf("write: %w", err)
	}

	// читаем кадры (разделитель 0x03), пока не встретим ответ с нашим id
	var buf bytes.Buffer
	tmp := make([]byte, 8192)
	for {
		n, err := conn.Read(tmp)
		if n > 0 {
			buf.Write(tmp[:n])
			for {
				idx := bytes.IndexByte(buf.Bytes(), etx)
				if idx < 0 {
					break
				}
				frame := make([]byte, idx)
				copy(frame, buf.Bytes()[:idx])
				buf.Next(idx + 1)

				var msg struct {
					ID     int             `json:"id"`
					Result json.RawMessage `json:"result"`
					Error  json.RawMessage `json:"error"`
				}
				if json.Unmarshal(frame, &msg) == nil && msg.ID == 1 && (msg.Result != nil || msg.Error != nil) {
					if msg.Error != nil {
						return nil, fmt.Errorf("klipper: %s", string(msg.Error))
					}
					return msg.Result, nil
				}
			}
		}
		if err != nil {
			return nil, fmt.Errorf("read: %w", err)
		}
	}
}

// queryKlipper возвращает result.status у objects/query.
func queryKlipper() (json.RawMessage, error) {
	res, err := klipperRequest("objects/query", map[string]interface{}{"objects": queryObjects})
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

// sendGcode отправляет gcode-скрипт в Klipper (метод gcode/script).
func sendGcode(script string) error {
	_, err := klipperRequest("gcode/script", map[string]interface{}{"script": script})
	return err
}

// cors проставляет заголовки и обрабатывает preflight. Возвращает true, если
// запрос был OPTIONS и уже обслужен (вызывающему нужно выйти).
func cors(w http.ResponseWriter, r *http.Request) bool {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return true
	}
	return false
}

func writeJSON(w http.ResponseWriter, code int, v interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

// ─── Камера: локальный MJPEG-стрим (mjpg_streamer) вместо облачного gkcam ───

const cameraDir = "/useremain/camera"

// cameraOn — True, если запущен mjpg_streamer (наш локальный стрим).
func cameraOn() bool {
	out, _ := exec.Command("sh", "-c", "ps | grep -v grep | grep -q mjpg_streamer && echo 1").Output()
	return strings.TrimSpace(string(out)) == "1"
}

// cameraAvailable — True, если на принтере установлены файлы камеры.
func cameraAvailable() bool {
	if _, err := os.Stat(cameraDir + "/mjpg_streamer"); err == nil {
		return true
	}
	return false
}

// runCamScript запускает cam-on.sh / cam-off.sh и возвращает их вывод.
func runCamScript(name string) (string, error) {
	out, err := exec.Command("sh", cameraDir+"/"+name).CombinedOutput()
	return strings.TrimSpace(string(out)), err
}

func main() {
	flag.Parse()

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write(indexHTML)
	})

	http.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		status, err := queryKlipper()
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Write(status)
	})

	// /control?cmd=pause|resume|cancel — управление текущей печатью.
	http.HandleFunc("/control", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST only"})
			return
		}
		var script string
		switch r.URL.Query().Get("cmd") {
		case "pause":
			script = "PAUSE"
		case "resume":
			script = "RESUME"
		case "cancel":
			script = "CANCEL_PRINT"
		default:
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "unknown cmd"})
			return
		}
		if err := sendGcode(script); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"ok": script})
	})

	// /gcode — произвольный скрипт {"script":"..."} (используется для температур).
	http.HandleFunc("/gcode", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST only"})
			return
		}
		var body struct {
			Script string `json:"script"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Script == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "empty script"})
			return
		}
		if err := sendGcode(body.Script); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"ok": body.Script})
	})

	// /version — собственная версия панели.
	http.HandleFunc("/version", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"version": version()})
	})

	// /update/check — сравнение с версией в репозитории.
	http.HandleFunc("/update/check", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		latest, err := fetchLatestVersion()
		if err != nil {
			writeJSON(w, http.StatusOK, map[string]interface{}{
				"current": version(), "latest": "", "available": false, "error": err.Error(),
			})
			return
		}
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"current":   version(),
			"latest":    latest,
			"available": latest != "" && latest != version(),
		})
	})

	// /update/apply — скачать свежий бинарник и перезапуститься.
	http.HandleFunc("/update/apply", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST only"})
			return
		}
		if err := applyUpdate(); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, http.StatusOK, map[string]string{"ok": "updating", "version": version()})
	})

	// /camera/status — что с камерой (установлена ли, включён ли локальный стрим).
	http.HandleFunc("/camera/status", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		writeJSON(w, http.StatusOK, map[string]interface{}{
			"available": cameraAvailable(),
			"on":        cameraOn(),
			"port":      8080,
		})
	})

	// /camera/on — заглушить gkcam и поднять локальный MJPEG-стрим.
	http.HandleFunc("/camera/on", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST only"})
			return
		}
		if !cameraAvailable() {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "камера не установлена (обновите панель из программы)"})
			return
		}
		out, err := runCamScript("cam-on.sh")
		if err != nil || !strings.Contains(out, "CAM_ON_OK") {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "не удалось запустить стрим: " + out})
			return
		}
		writeJSON(w, http.StatusOK, map[string]interface{}{"on": true, "port": 8080})
	})

	// /camera/off — остановить локальный стрим и вернуть штатную камеру (gkcam).
	http.HandleFunc("/camera/off", func(w http.ResponseWriter, r *http.Request) {
		if cors(w, r) {
			return
		}
		if r.Method != http.MethodPost {
			writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST only"})
			return
		}
		out, err := runCamScript("cam-off.sh")
		if err != nil || !strings.Contains(out, "CAM_OFF_OK") {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": "не удалось вернуть gkcam: " + out})
			return
		}
		writeJSON(w, http.StatusOK, map[string]interface{}{"on": false})
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		fmt.Fprint(w, "ok")
	})

	log.Printf("gkbridge %s: слушаю %s, сокет %s", version(), *listenAddr, *socketPath)
	log.Fatal(http.ListenAndServe(*listenAddr, nil))
}
