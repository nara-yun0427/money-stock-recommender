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

## 배포 (무료 클라우드 호스팅 — 어디서나 휴대폰으로 접속)

PC를 켜두거나 같은 Wi-Fi에 있을 필요 없이, 데이터가 켜져 있는 휴대폰
어디서나 접속하려면 무료 클라우드 서버에 올려야 합니다. **Render(웹 서버,
무료, 카드 등록 불필요) + Neon(Postgres DB, 무료, 카드 등록 불필요)** 조합을
권장합니다. 저장소 루트의 `render.yaml`이 배포를 대부분 자동화해줍니다.

### 1. GitHub에 코드 올리기

Render는 GitHub 저장소에서 코드를 읽어 배포합니다. 이 저장소를 GitHub에
push해야 합니다 (Claude에게 "push해줘"라고 요청하시면 진행해 드립니다).

### 2. Neon에서 무료 Postgres 만들기 (거래 내역을 안전하게 보관)

1. [neon.tech](https://neon.tech)에서 무료 계정 생성 (GitHub 계정으로 가입 가능)
2. 새 프로젝트 생성 → 기본 데이터베이스가 자동으로 만들어짐
3. 대시보드에서 **Connection string**을 복사 (`postgresql://...`로 시작)
   — 이 값을 3단계에서 `DATABASE_URL`에 붙여넣을 것입니다

### 3. Render에서 배포하기

1. [render.com](https://render.com)에서 무료 계정 생성 (GitHub 계정으로 가입 가능)
2. 대시보드에서 **New → Blueprint** 선택 → 이 GitHub 저장소 연결
3. Render가 저장소 루트의 `render.yaml`을 자동으로 인식해서 `my-budget-app`
   웹 서비스(무료 플랜, `budget/Dockerfile` 사용)를 구성해줍니다
4. 배포 전 환경변수 입력을 요구하는데, 아래 값을 입력하세요:

   | 환경변수 | 값 |
   | --- | --- |
   | `BUDGET_PIN` | 원하는 로그인 PIN (숫자 4자리 이상 권장) |
   | `DATABASE_URL` | 2단계에서 복사한 Neon connection string |
   | `SECRET_KEY` | 자동 생성됨 (그대로 두면 됨) |
   | `COOKIE_SECURE` | 자동으로 `true` 설정됨 |

5. **Apply**를 누르면 빌드가 시작되고, 몇 분 후 `https://my-budget-app-xxxx.onrender.com`
   같은 공개 HTTPS 주소가 생깁니다. 이 주소로 휴대폰 데이터/어떤 Wi-Fi에서든
   접속할 수 있습니다.
6. 휴대폰 브라우저로 그 주소에 접속 → PIN 입력 → 브라우저 메뉴에서 "홈 화면에
   추가"를 누르면 앱 아이콘처럼 설치됩니다.

### 참고: 무료 플랜의 제약

- Render 무료 웹 서비스는 15분간 요청이 없으면 잠자기 상태로 들어가고,
  다음 접속 시 다시 깨어나는 데 30~50초 정도 걸립니다(그 이후엔 빠릅니다).
  매일 쓰는 개인 가계부 용도로는 이 정도 지연은 대체로 무리 없지만, 완전히
  즉시 반응하는 게 중요하다면 Render의 유료 플랜(콜드 스타트 없음)을
  고려하세요.
- Neon 무료 티어는 카드 등록 없이 영구적으로 사용 가능한 무료 구간을
  제공합니다(용량 제한 내에서). 거래 내역 데이터양 자체가 작아서 개인
  가계부 용도로는 충분합니다.

### 환경변수 요약

| 환경변수 | 설명 |
| --- | --- |
| `BUDGET_PIN` | 로그인 PIN (기본값 `1234`는 로컬 전용 — 배포 시 반드시 변경) |
| `SECRET_KEY` | 세션 쿠키 서명 키 (`render.yaml`이 배포 시 자동 생성) |
| `COOKIE_SECURE` | `true`로 설정하면 HTTPS에서만 쿠키 전송 (배포 환경 권장, `render.yaml`이 자동 설정) |
| `DATABASE_URL` | 미설정 시 컨테이너 내부 SQLite 파일 사용(로컬 전용). **무료 호스팅은 재배포/재시작 시 파일이 사라질 수 있어**, 거래 내역처럼 다시 만들 수 없는 데이터는 Neon 같은 외부 DB 연결 문자열을 권장합니다 |

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
