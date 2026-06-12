// gkbridge — крошечный мост между Klipper-сокетом GoKlipper (gklib) и HTTP.
// Читает /tmp/unix_uds1 (урезанный Klipper API, JSON-кадры с терминатором 0x03),
// отдаёт чистый JSON по HTTP с CORS, чтобы статичная веб-панель могла опрашивать
// принтер прямо из браузера.
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
	"print_stats":   nil,
	"virtual_sdcard": nil,
	"extruder":      nil,
	"heater_bed":    nil,
	"chamber_temp":  nil,
	"toolhead":      nil,
	"gcode_move":    nil,
	"fan":           nil,
	"filament_hub":  nil,
}

var (
	socketPath = flag.String("socket", "/tmp/unix_uds1", "путь к unix-сокету gklib")
	listenAddr = flag.String("addr", ":8088", "адрес HTTP-сервера")
)

// queryKlipper открывает свежее соединение с сокетом, шлёт objects/query,
// читает ответ до байта 0x03 и возвращает поле result.status.
func queryKlipper() (json.RawMessage, error) {
	conn, err := net.DialTimeout("unix", *socketPath, 3*time.Second)
	if err != nil {
		return nil, fmt.Errorf("dial: %w", err)
	}
	defer conn.Close()

	req := map[string]interface{}{
		"method": "objects/query",
		"params": map[string]interface{}{"objects": queryObjects},
		"id":     1,
	}
	payload, _ := json.Marshal(req)
	payload = append(payload, etx)

	conn.SetDeadline(time.Now().Add(4 * time.Second))
	if _, err := conn.Write(payload); err != nil {
		return nil, fmt.Errorf("write: %w", err)
	}

	// читаем кадры до тех пор, пока не встретим ответ с нашим id и полем result
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
				}
				if json.Unmarshal(frame, &msg) == nil && msg.ID == 1 && msg.Result != nil {
					var res struct {
						EventTime float64         `json:"eventtime"`
						Status    json.RawMessage `json:"status"`
					}
					if json.Unmarshal(msg.Result, &res) == nil && res.Status != nil {
						return res.Status, nil
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
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		status, err := queryKlipper()
		if err != nil {
			w.WriteHeader(http.StatusBadGateway)
			json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}
		w.Write(status)
	})

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		fmt.Fprint(w, "ok")
	})

	log.Printf("gkbridge: слушаю %s, сокет %s", *listenAddr, *socketPath)
	log.Fatal(http.ListenAndServe(*listenAddr, nil))
}
