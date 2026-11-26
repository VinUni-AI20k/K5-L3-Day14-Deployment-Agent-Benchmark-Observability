# Day 14 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (`01-localhost-vs-production/develop/app.py`)

1. **Hardcode secret trong code**: `OPENAI_API_KEY = "sk-hardcoded-..."` và `DATABASE_URL` chứa `admin:password123`. Push lên GitHub là ai cũng đọc được key và mật khẩu DB.
2. **Log ra secret**: `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`. Key bị in vào log, mà log thường được nhiều người và nhiều hệ thống đọc.
3. **Không có config management**: `DEBUG = True`, `MAX_TOKENS = 500` ghi cứng. Muốn đổi giữa dev và production thì phải sửa code rồi deploy lại.
4. **Dùng `print()` thay vì logging**: không có level (INFO/ERROR), không có định dạng JSON, công cụ quản lý log không lọc hay tìm kiếm được.
5. **Không có health check** (`/health`, `/ready`): app crash hay treo thì nền tảng cloud không biết để restart hoặc ngừng gửi traffic vào.
6. **Port cố định `8000`**: Railway/Render cấp port qua biến môi trường `PORT`, ghi cứng thì app không nhận được request.
7. **`host="localhost"`**: chỉ nhận kết nối từ chính máy đó. Chạy trong container/cloud thì bên ngoài không gọi vào được, phải dùng `0.0.0.0`.
8. **`reload=True`**: chế độ tự nạp lại code chỉ dành cho lúc dev, tốn tài nguyên và không ổn định khi chạy production.
9. **Không xử lý shutdown**: không bắt tín hiệu SIGTERM, khi nền tảng tắt app thì request đang chạy bị cắt ngang.

### Exercise 1.2: Kết quả chạy bản develop

```text
$ curl.exe -X POST "http://localhost:8000/ask?question=Hello"
INFO:     127.0.0.1:53867 - "POST /ask?question=Hello HTTP/1.1" 200 OK
[DEBUG] Got question: Hello
[DEBUG] Using key: sk-hardcoded-fake-key-never-do-this
[DEBUG] Response: Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.
```

Quan sát: app chạy được, nhưng terminal in ra cả `Using key: sk-hardcoded-...`, tức là secret bị lộ trong log. Chạy được chưa có nghĩa là production-ready.

### Exercise 1.3: Comparison table

| Feature | Develop | Production | Tại sao quan trọng? |
|---------|---------|------------|---------------------|
| Config | Hardcode trong `app.py` | Đọc từ env vars qua `config.py` (`os.getenv`) | Không lộ secret khi push code; cùng một code chạy được ở dev/staging/prod chỉ bằng cách đổi biến môi trường |
| Secrets | Key + mật khẩu DB ghi trong code, còn bị `print` ra | Lấy từ env, không bao giờ log secret (chỉ log `question_length`) | Lộ key là mất tiền và mất dữ liệu |
| Health check | Không có | `/health` (liveness) và `/ready` (readiness, trả 503 khi chưa sẵn sàng) | Platform biết khi nào cần restart app và khi nào được gửi traffic vào |
| Logging | `print()` | Logging có level, định dạng JSON | Dễ tìm, lọc và cảnh báo trong Datadog/Loki/Grafana |
| Shutdown | Đột ngột | Graceful: `lifespan` + bắt `SIGTERM`, chờ request đang chạy xong | Không làm hỏng request của người dùng khi deploy bản mới hoặc scale down |
| Host / Port | `localhost:8000` cố định | `HOST=0.0.0.0`, `PORT` lấy từ env | Chạy được trong container và trên cloud |
| Reload / Debug | `reload=True` luôn bật | Chỉ bật khi `DEBUG=true` | Production cần ổn định, không tự nạp lại code |

### Kết quả chạy bản production (quan sát thực tế)

```text
POST /ask  -> 200 OK, trả về JSON {"answer": "...", "model": ...}
GET  /health -> {"status": "ok", "uptime_seconds": 58.5, "version": "1.0.0", "environment": "development"}
Log: "Uvicorn running on http://0.0.0.0:8000"
Log: "WARNING: OPENAI_API_KEY not set — using mock LLM"
Log: không có dòng "Using key: ..." (secret không bị in ra)
```

Nhận xét:
- Bản production dùng `0.0.0.0` và đọc cấu hình từ env, nên cùng một code có thể chạy ở nhiều môi trường.
- Thiếu `OPENAI_API_KEY` thì app không crash, mà tự chuyển sang mock LLM và ghi cảnh báo. Đây là cách xử lý có chủ đích.
- `/health` cho platform biết app còn sống và đang chạy bao lâu.
- Log ở bản production không in secret. Chưa rõ vì sao các dòng log JSON do app ghi không hiện trong terminal, cần tìm hiểu thêm.

## Part 2: Docker

### Exercise 2.1: Dockerfile questions (`02-docker/develop/Dockerfile`)
1. **Base image**: `python:3.11`, image Python đầy đủ (~1 GB), có sẵn Python 3.11.
2. **Working directory**: `/app`, thư mục làm việc bên trong container. Các lệnh sau đó chạy ở đây.
3. **Vì sao COPY requirements.txt trước**: Docker cache theo từng bước. Nếu chỉ sửa code mà requirements không đổi, Docker dùng lại bước `pip install` đã cache, build nhanh hơn. Copy code trước thì mỗi lần sửa code phải cài lại toàn bộ thư viện.
4. **CMD vs ENTRYPOINT**: `CMD` là lệnh mặc định, có thể bị ghi đè khi `docker run` kèm lệnh khác. `ENTRYPOINT` là lệnh cố định, tham số thêm vào được nối sau nó. Dockerfile develop dùng `CMD ["python", "app.py"]`.

### Exercise 2.2: Build và chạy
- Lệnh build: `docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .`
- Test: `curl.exe -X POST "http://localhost:8000/ask?question=What%20is%20Docker"` trả về `{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}`

### Exercise 2.3: Image size comparison

| Image | Content size | Disk usage |
|-------|--------------|------------|
| `my-agent:develop` (single-stage) | 426 MB | 1.67 GB |
| `my-agent:advanced` (multi-stage) | 57.4 MB | 240 MB |

- Chênh lệch: bản advanced nhỏ hơn **86,5%** theo content size (426 → 57.4 MB), và **85,6%** theo disk usage.
- Vì sao nhỏ hơn: stage `builder` có gcc và công cụ build để cài thư viện, nhưng stage đó không được copy sang image cuối. Image cuối chỉ có Python slim và thư viện đã cài.

### Exercise 2.4: Docker Compose stack
- Dịch vụ được start: `agent`, `redis`, `qdrant`, `nginx`.
- Luồng request: người dùng → `nginx` (cổng 80, giới hạn tốc độ) → `agent` (qua mạng nội bộ `internal`) → `redis` và `qdrant`. Chỉ `nginx` mở cổng ra ngoài.
- `agent` chờ `redis` và `qdrant` báo healthy rồi mới khởi động (`depends_on`).
- Test qua Nginx: `GET /health` trả `status: ok`, `POST /ask` trả về câu trả lời của agent.
- Lệnh đã dùng: `docker compose -p k5-day14-docker up -d --build`.

## Part 3: Cloud Deployment

_(làm sau Part 6)_

## Part 4: API Security

### Exercise 4.1: API Key authentication (`04-api-gateway/develop/app.py`)
- **Key được check ở đâu**: trong hàm `verify_api_key`, gắn vào `/ask` qua `Depends(...)`. Key đọc từ biến môi trường `AGENT_API_KEY`.
- **Sai key thì sao**: thiếu header trả **401**, sai key trả **403**.
- **Rotate key**: đổi giá trị `AGENT_API_KEY` rồi khởi động lại app. Key cũ lập tức không dùng được.
- Kết quả đo: không có key → `HTTP 401`; có key `secret-key-123` → trả về câu trả lời.

### Exercise 4.2: JWT authentication (`04-api-gateway/production/`)
- Lấy token qua `POST /auth/token` với `student` / `demo123`. Lưu ý: hướng dẫn trong CODE_LAB ghi `/token` với `admin` / `secret` là không đúng với repo.
- Dùng token: header `Authorization: Bearer <token>` cho `/ask`.
- Token có thời hạn 60 phút (`ACCESS_TOKEN_EXPIRE_MINUTES`), hết hạn thì phải đăng nhập lại.

### Exercise 4.3: Rate limiting (`rate_limiter.py`)
- **Thuật toán**: sliding window (cửa sổ trượt). Mỗi user có deque các timestamp, cửa sổ 60 giây.
- **Giới hạn**: user thường 10 request/phút, admin 100 request/phút.
- **Bypass cho admin**: không bypass, admin dùng một bộ đếm riêng (`rate_limiter_admin`) với giới hạn cao hơn.
- Kết quả đo: chạy 12 lần `/ask` liên tiếp, các request vượt giới hạn trả **429**. Bộ đếm tính cả request đã gửi trước đó trong 60 giây gần nhất.

### Exercise 4.4: Cost guard (`cost_guard.py`)
- Mỗi user có ngân sách $1/ngày, tổng toàn hệ thống $10/ngày.
- Vượt ngân sách của user trả **402**, vượt ngân sách toàn hệ thống trả **503**.
- Chi phí được tính từ số token input và output nhân với giá mỗi 1K token.
- Bản này lưu trong bộ nhớ, nên mất khi restart. Production thật cần lưu ở Redis hoặc database.
- Vì sao cần cả rate limit và cost guard: rate limit chặn tốc độ gọi, cost guard chặn tổng tiền. Một user có thể gọi chậm nhưng vẫn đốt hết tiền nếu không có cost guard.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks (`05-scaling-reliability/develop/`)
- `GET /health` (liveness): app còn sống, trả `status: ok` và uptime.
- `GET /ready` (readiness): app đã load xong và sẵn sàng nhận request. Đây là lúc mình kiểm tra `/ready` trước khi gửi traffic.
- Kết quả đo: _(dán kết quả `Invoke-RestMethod` của `/health` và `/ready` vào đây; mục này chưa có số đo)_

### Exercise 5.2: Graceful shutdown
- Middleware đếm số request đang xử lý (`_in_flight_requests`).
- Khi tắt, app đặt `_is_ready = False`, rồi chờ request đang chạy xong (tối đa 30 giây) trước khi thoát.
- Nhận xét: nhờ vậy request đang xử lý không bị cắt ngang khi deploy hoặc scale down.

### Exercise 5.3: Stateless design (`05-scaling-reliability/production/`)
- Anti-pattern: lưu lịch sử hội thoại trong dict của RAM. Khi scale ra nhiều instance, mỗi instance có một dict riêng, nên request sau có thể rơi vào instance không có lịch sử.
- Cách làm đúng: lưu lịch sử trong Redis (chung cho mọi instance), instance nào cũng đọc được.

### Exercise 5.4: Load balancing với 3 instance
- Lệnh: `docker compose -p k5-day14-scaling up -d --build --scale agent=3`
- Kết quả `test_stateless.py`: 5 request được phục vụ bởi 3 instance khác nhau (`instance-6d745c`, `instance-9157b3`, `instance-6841d3`), tất cả đều thành công.
- Lịch sử hội thoại có đủ 10 message (5 câu hỏi và 5 câu trả lời), dù các request chạy trên nhiều instance.
- Kết luận: state nằm ở Redis, không nằm ở RAM của từng instance, nên stack là stateless.

### Exercise 5.5: Kiểm tra failover
- Chưa thực hiện. Đây là bước tùy chọn (dừng một instance để xem traffic chuyển đi), không nằm trong checkpoint CP4 của lớp K5.

## Part 6: Final Project

### Output `check_production_ready.py` (chạy đầy đủ, có Docker)

```text
================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ✅ Graceful shutdown
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 12/12 tiêu chí đạt · 41/41 checks passed
  🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
================================================================
```

Một số số liệu từ lần chạy: image 273 MB, `docker stop` thoát với exit code 0 trong 1.0s, SIGTERM lúc đang có request → request vẫn 200 và process thoát với exit code 0.

### Ghi chú môi trường chạy script chấm

Máy Windows của tôi không mở được Ubuntu trên WSL (lỗi `Wsl/Service/E_UNEXPECTED`, đã thử gỡ và cài lại). Vì Python trên Windows không gửi được SIGTERM, tôi chạy **script chấm gốc, không sửa**, trong một container Linux của Docker Desktop. Container có Python 3.11, cài `requirements.txt`, và Docker CLI dùng chung Docker daemon của máy qua `/var/run/docker.sock`.

Dockerfile của container chấm:

```dockerfile
FROM docker:27-cli AS dockercli

FROM python:3.11-slim
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=dockercli /usr/local/libexec/docker/cli-plugins /usr/local/libexec/docker/cli-plugins
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
```

Lệnh chạy (PowerShell, từ gốc repo; mount cả repo để script thấy `.gitignore` ở thư mục cha):

```powershell
docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock -v "${PWD}:/repo" -w /repo/06-lab-complete k5-checker python check_production_ready.py
```

### Tóm tắt cách làm từng tiêu chí

| # | Tiêu chí | Cách làm |
|---|----------|----------|
| 1 | Dockerfile | 2 stage: `builder` tạo venv và cài thư viện, `runtime` (`python:3.11-slim`) chỉ copy venv + code, user non-root `app`, có `HEALTHCHECK`, CMD `sh -c "exec uvicorn ... --port ${PORT:-8000}"` để uvicorn là PID 1 |
| 2 | docker-compose | Service `agent` build từ Dockerfile, `REDIS_URL=redis://redis:6379/0`, `depends_on` Redis healthy; service `redis:7-alpine` có healthcheck |
| 3 | .dockerignore | Loại `.env`, `__pycache__`, `venv`, `.git`, tài liệu, `benchmark-observability/` |
| 4 | `/health` | Luôn trả 200 khi process còn chạy, không phụ thuộc Redis |
| 5 | `/ready` | Ping Redis; lỗi kết nối → 503 |
| 6 | API key | `APIKeyHeader("X-API-Key")`, so với `AGENT_API_KEY`; thiếu/sai → 401 |
| 7 | Rate limit | Sliding window bằng Redis sorted set (`ZREMRANGEBYSCORE` → `ZCARD` → `ZADD` → `EXPIRE`), vượt → 429 kèm `Retry-After`; state ở Redis nên restart vẫn còn |
| 8 | Cost guard | Cộng dồn chi phí theo ngày vào Redis (`INCRBYFLOAT`), vượt `DAILY_BUDGET_USD` → 402 |
| 9 | Config | `config.py` đọc mọi giá trị bằng `os.getenv`; `.env.example` liệt kê đủ biến, không có secret |
| 10 | Logging | `JsonFormatter` tự viết, mỗi dòng log là một JSON object; middleware log mỗi request (method, path, status, ms) |
| 11 | Graceful shutdown | Dùng `lifespan` của FastAPI; không tự đăng ký handler SIGTERM, để uvicorn tự ngừng nhận request mới và chờ request đang chạy xong |
| 12 | Deploy config | `railway.toml`: `builder = "DOCKERFILE"`, `healthcheckPath = "/health"`; app đọc `PORT` |

## AI log

- Dùng Claude Code để đọc repo, giải thích các anti-pattern ở Part 1 và soạn nháp bảng so sánh. Tôi tự chạy app và tự kiểm tra lại từng ý.
- Part 2, 4, 5: Claude Code giải thích Dockerfile, compose, JWT, rate limit, stateless và hướng dẫn lệnh PowerShell; tôi tự chạy các lệnh và dán kết quả thật.
- Part 6: Claude Code viết code cho các TODO (`main.py`, `auth.py`, `rate_limiter.py`, `cost_guard.py`, `config.py`, `redis_client.py`, Dockerfile, compose, `.dockerignore`, `.env.example`, `railway.toml`) và giải thích từng phần. Khi WSL Ubuntu bị lỗi, Claude Code dựng container Linux để chạy script chấm gốc, đạt PASS 12/12.
