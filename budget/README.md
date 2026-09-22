# 내 가계부 (개인용)

매일 지출을 카테고리·결제수단과 함께 몇 초 만에 기록하고, 주간/월간/연간
대시보드로 어디에 가장 많이 썼는지·지난달 대비·작년 동기간 대비를 한눈에
확인하는 개인용 가계부 앱입니다. (국내주식 추천 앱과는 완전히 독립된
프로젝트입니다 — 코드도, 배포도 공유하지 않습니다.)

## 카테고리 & 결제수단

- 카테고리: 고정지출 / 쇼핑 / 장보기 / 외식 / 카페 / 문화생활 / 기타
- 결제수단: 신용카드 / 체크카드 / 현금 — 결제수단별 대시보드는 신용 65% ·
  체크 25% · 현금 10%를 목표 비율로 함께 보여줍니다.

카테고리는 `backend/app/seed.py`에서 이름·아이콘·색상을 바꿀 수 있습니다
(DB가 비어 있을 때만 최초 1회 시드됩니다).

## 로그인

회원가입 없이 PIN 하나로만 보호합니다. `BUDGET_PIN` 환경변수(기본값
`1234` — **반드시 바꿔서 사용하세요**)로 설정하고, 로그인하면 서명된 쿠키가
30일간 유지됩니다.

## 실행 방법 (로컬)

### 최초 1회 설정

```bash
cd budget/backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

cd ../frontend
npm install
npm run build
```

### 실행

`budget/start.bat`을 더블클릭하면 서버가 켜집니다 (`http://localhost:8010`).
휴대폰에서는 같은 Wi-Fi에서 `http://<PC-IP>:8010`으로 접속 후 "홈 화면에
추가"로 PWA처럼 설치할 수 있습니다.

### 개발 모드 (핫리로드)

```bash
cd budget/backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
```

```bash
cd budget/frontend
npm run dev
```

`frontend`를 고칠 때는 `npm run dev`로 확인하고, 실제로 쓸 때는
`npm run build` 후 `start.bat`으로 실행하세요.

## 배포 (무료 클라우드 호스팅)

`budget/Dockerfile`은 프론트엔드 빌드 + 백엔드를 하나의 이미지로 묶는
멀티스테이지 빌드입니다. Render 등 무료 호스팅에 올릴 때는 아래 환경변수를
반드시 설정하세요.

| 환경변수 | 설명 |
| --- | --- |
| `BUDGET_PIN` | 로그인 PIN (기본값 `1234`는 로컬 전용 — 배포 시 반드시 변경) |
| `SECRET_KEY` | 세션 쿠키 서명 키 (배포 시 임의의 긴 문자열로 변경) |
| `COOKIE_SECURE` | `true`로 설정하면 HTTPS에서만 쿠키 전송 (배포 환경 권장) |
| `DATABASE_URL` | 미설정 시 컨테이너 내부 SQLite 파일 사용. **무료 호스팅은 재배포/재시작 시 파일이 사라질 수 있어**, 거래 내역처럼 다시 만들 수 없는 데이터는 외부 DB를 권장합니다 — 예: [Neon](https://neon.tech) 무료 Postgres에서 발급받은 연결 문자열(`postgresql://...`) |

## 프로젝트 구조

- `backend/` — FastAPI + SQLAlchemy. PIN 세션 인증, 거래 CRUD, 기간별 대시보드
  집계(`app/dashboard.py`)를 제공합니다. 로컬 SQLite는 `backend/data/budget.db`.
- `frontend/` — React + Vite PWA. `npm run build`로 만든 `frontend/dist`를
  백엔드가 그대로 서빙합니다(별도 웹서버 불필요).

## 대시보드가 보여주는 것

- 주간 / 월간 / 연간 단위로 전환하며 이전 기간(지난주·지난달·작년) 대비,
  그리고 작년 동기간 대비 증감액·증감률
- 카테고리별 도넛 차트 + 금액/비율
- 결제수단별 실제 비율 vs 목표 비율(65/25/10) 비교 막대
- 기간 내 일별(주간·월간) 또는 월별(연간) 지출 추이
