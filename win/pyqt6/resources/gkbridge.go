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
	_ "embed"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"time"
)

//go:embed index.html
var indexHTML []byte

const etx = 0x03 // терминатор кадра Klipper API

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

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		fmt.Fprint(w, "ok")
	})

	log.Printf("gkbridge: слушаю %s, сокет %s", *listenAddr, *socketPath)
	log.Fatal(http.ListenAndServe(*listenAddr, nil))
}
