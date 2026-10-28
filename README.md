# English Learning Platform

單人使用的英語聽力與跟讀練習平台（不需登入）。播放使用 YouTube 內嵌播放器，後端只抓英文字幕，不下載影片。

目前包含後端 API 與前端練習頁。中文翻譯（依 `OPENAI_API_KEY` 快取）會在下一個階段接上；還沒有翻譯時，練習頁的「英文＋中文」會顯示說明，英文練習不受影響。

## 需求

- Python 3.11 或以上
- Node.js 20 或以上

## 本地執行

開兩個終端機。

後端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打開 <http://127.0.0.1:5173>。開發伺服器會把 `/api` 轉到後端。API 文件在 <http://127.0.0.1:8000/docs>。

資料庫預設是 `backend/data/app.db`。想換位置可以設定：

```bash
export DATABASE_URL=sqlite:////absolute/path/to/app.db
```

### 匯入一支影片

```bash
curl -s -X POST http://127.0.0.1:8000/api/videos \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=lC_-9TD3TfA"}'
```

也可以直接用指令列：

```bash
python -m app.cli "https://www.youtube.com/watch?v=lC_-9TD3TfA"
```

同一支影片再匯入一次會直接回傳已儲存的資料，不會重複抓字幕。

### 主要端點

| 方法 | 路徑 | 說明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康檢查 |
| `GET` | `/api/videos` | 影片列表 |
| `POST` | `/api/videos` | 以 `{ "url": "..." }` 匯入影片並切段 |
| `GET` | `/api/videos/{id}` | 影片與全部分段 |
| `GET` | `/api/videos/{id}/segments` | 分段列表 |

分段欄位包含 `text`、`start_time`、`end_time`（秒）。字幕優先使用手動英文（`en`、`en-US`、`en-GB` 等），沒有才改用自動產生的英文字幕。`caption_source` 會是 `manual` 或 `generated`。

跟讀片段大約 1–3 句、5–15 秒，盡量在句號、問號、驚嘆號切開。單句超過 15 秒時，會再依逗號等子句或時間切開。

## 錯誤訊息

失敗時回應格式為：

```json
{"detail": {"code": "youtube_blocked", "message": "..."}}
```

常見代碼：

- `invalid_url`：不是有效的 YouTube 影片網址
- `no_english_captions`：沒有英文手動或自動字幕
- `transcripts_disabled`：影片關閉字幕
- `video_unavailable`：影片不存在或無法觀看
- `youtube_blocked`：YouTube 擋住這台機器的 IP
- `no_spoken_content`：字幕裡沒有可練習的口語

YouTube 常會擋住雲端或資料中心 IP。若出現 `youtube_blocked`，可以設定 HTTP 代理後重開服務：

```bash
export YOUTUBE_PROXY_URL=http://user:pass@host:port
```

沒有代理時，其他功能與測試仍可運作；匯入會回傳清楚的錯誤，不會讓服務當掉。

## 頁面

- `/`：貼上 YouTube 網址、看已匯入的影片
- `/videos/{id}`：該片的跟讀片段
- `/videos/{id}/segments/{position}`：只播放該段。可重播、上一段／下一段，速度為 0.8、0.9、1.0。進入時不顯示字幕，側欄可改成英文，或英文＋中文。英文旁可複製。

## 測試

```bash
cd backend
source .venv/bin/activate
pytest
```

```bash
cd frontend
npm test
```

字幕抓取在單元測試裡使用假的 YouTube 回應，所以不需要網路，也不需要 `OPENAI_API_KEY`。
