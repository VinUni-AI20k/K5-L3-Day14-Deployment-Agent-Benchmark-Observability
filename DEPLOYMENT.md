# Deployment Information

## Trạng thái: CHƯA DEPLOY

Agent chưa được deploy lên cloud và **chưa có URL public**. Lý do: deploy cần đăng nhập tài khoản Railway hoặc Render của người học. Lệnh đăng nhập Railway CLI đã được chạy hai lần nhưng không được xác nhận (một lần lỗi `invalid_grant`, một lần hết giờ sau 5 phút).

Đã kiểm tra trên máy (không phải trên cloud): `check_production_ready.py` đạt 12/12 (43/43), gồm `/health`, `/ready`, 401, 200, 429, 402.

## Cách deploy

Code deploy nằm trên nhánh `theduythg/hieu`.

### Cách 1: Render (không cần cài CLI)
1. render.com → **New → Blueprint** → chọn repo.
2. Branch: `theduythg/hieu` (hoặc `main` sau khi đã merge). Blueprint Path: `06-lab-complete/render.yaml`.
3. **Apply**. Lấy `AGENT_API_KEY` trong mục Environment của service.

`render.yaml` chưa được chạy thử trên Render.

### Cách 2: Railway CLI
```bash
npx -y @railway/cli login
cd 06-lab-complete
npx -y @railway/cli init
npx -y @railway/cli add --database redis
```
Sau đó tạo service cho agent, đặt `REDIS_URL` trỏ tới Redis vừa tạo, đặt `AGENT_API_KEY` ngẫu nhiên, chạy `npx -y @railway/cli up`, rồi `npx -y @railway/cli domain`.

## Lệnh kiểm tra sau khi deploy

```bash
BASE=<URL public thật>
read -rs AGENT_API_KEY

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"     # kỳ vọng 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"      # kỳ vọng 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'   # kỳ vọng 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'   # kỳ vọng 200
```

## Biến môi trường cần đặt trên nền tảng

| Biến | Giá trị |
|---|---|
| `AGENT_API_KEY` | Chuỗi bí mật ngẫu nhiên, chỉ đặt trên nền tảng |
| `REDIS_URL` | Chuỗi kết nối Redis của nền tảng |
| `ENVIRONMENT` | `production` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `DAILY_BUDGET_USD` | `1.0` |
| `PORT` | Nền tảng tự cấp |

## Screenshots (chưa có, chụp sau khi deploy)
`screenshots/dashboard.png`, `screenshots/running.png`, `screenshots/test.png`
