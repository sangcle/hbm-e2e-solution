# HBM E2E 배포 매뉴얼

## 배포 메타데이터

- 서비스명: HBM E2E Design Workbench
- 저장소: `https://github.com/sangcle/hbm-e2e-solution`
- 배포 담당 LinkedIn ID: `minyong-choi-a60645260`
- LinkedIn URL: `https://www.linkedin.com/in/minyong-choi-a60645260/`
- 기본 백엔드 URL: `http://127.0.0.1:8000`
- 기본 프론트엔드 URL: `http://127.0.0.1:5173`

LinkedIn ID는 프로필 주소의 `/in/` 뒤에 오는 값입니다. 현재 배포 담당 LinkedIn ID는
`minyong-choi-a60645260`입니다.

## 배포 구성

- Backend: FastAPI, Uvicorn
- Frontend: React, Vite
- Simulation backend: Analytical model, optional Ramulator2 runtime bundle
- Runtime bundle: `runtime/ramulator2`
- Result storage: `results/<run_id>/`
- Process calibration profiles: `backend/app/calibration/process/*.json`
- License: MIT
- Third-party notices: `THIRD_PARTY_NOTICES.md`

## 사전 준비

Windows PowerShell 기준입니다.

```powershell
cd C:\E2E
python --version
node --version
npm --version
```

권장 버전:

- Python 3.11
- Node.js 20 이상
- npm 10 이상

## Backend 설치

```powershell
cd C:\E2E
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

Ramulator2 런타임 번들을 사용할 경우:

```powershell
$env:RAMULATOR2_HOME = "C:\E2E\runtime\ramulator2"
```

## Frontend 설치

```powershell
cd C:\E2E\frontend
npm install
```

## 로컬 배포 실행

Backend:

```powershell
cd C:\E2E
$env:RAMULATOR2_HOME = "C:\E2E\runtime\ramulator2"
$env:HBM_E2E_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd C:\E2E\frontend
$env:VITE_API_BASE = "http://127.0.0.1:8000"
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저에서 `http://127.0.0.1:5173`을 엽니다.

5173 이외의 로컬 Vite 포트를 사용할 때만 다음 값을 추가로 설정합니다.

```powershell
$env:HBM_E2E_CORS_ALLOW_LOCAL_DEV_PORTS = "true"
```

## Production 빌드

```powershell
cd C:\E2E\frontend
$env:VITE_API_BASE = "http://127.0.0.1:8000"
npm run build
```

빌드 결과는 `frontend/dist/`에 생성됩니다.

운영 배포에서는 백엔드 시작 전에 CORS를 정확한 프론트엔드 도메인으로 제한합니다.

```powershell
$env:HBM_E2E_CORS_ORIGINS = "https://your-production-frontend.example.com"
$env:HBM_E2E_CORS_ALLOW_LOCAL_DEV_PORTS = "false"
```

정적 파일 서버로 확인:

```powershell
cd C:\E2E\frontend
npm run preview -- --host 127.0.0.1 --port 4173
```

## 배포 후 확인

Backend health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Ramulator2 status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/backends/ramulator2/status
```

Frontend:

- 상단 상태가 `API online`인지 확인
- Ramulator2 runtime이 정상인 경우 `Ramulator2 available`인지 확인
- `Run` 실행 후 `results/<run_id>/result.json`과 `report.md` 생성 확인

## 공정 파라미터 배포 확인

프론트 왼쪽 패널의 `Process Quality`에서 `Enable process proxy`를 켜면 공정 품질 파라미터를 입력할 수 있습니다.

실제 측정 기반 보정을 사용할 경우:

- 새 보정 profile JSON을 `backend/app/calibration/process/`에 추가
- 요청의 `process_parameters.calculation_mode`를 `calibrated`로 설정
- `process_parameters.calibration_artifact_id`를 새 profile의 `artifact_id`로 설정
- `process_parameters.source_type`을 `internal_measurement`로 설정
- `process_parameters.calibration_status`를 `calibrated`로 설정

## 운영 시 주의사항

- `ramulator2/` 전체 소스 폴더는 저장소 배포 대상에서 제외합니다.
- 배포에는 `runtime/ramulator2` 번들을 사용합니다.
- Ramulator2 런타임 번들은 MIT 라이선스이며 `runtime/ramulator2/LICENSE`와 `THIRD_PARTY_NOTICES.md`를 함께 유지합니다.
- `results/`는 실행 결과 저장소이므로 정기적으로 보관 또는 정리합니다.
- 공개 proxy 공정 계수는 방향성 비교용입니다.
- 실제 공정 데이터가 들어오면 calibration profile을 별도 artifact로 관리합니다.
- 외부 공개 배포 전에는 CORS 허용 도메인을 운영 도메인으로 제한하세요.

## 릴리즈 체크리스트

- [x] LinkedIn ID를 실제 ID로 교체
- [x] 루트 `LICENSE` 추가
- [x] `THIRD_PARTY_NOTICES.md` 추가
- [x] Ramulator2 runtime license/provenance 확인
- [x] synthetic calibration example 명시
- [ ] `README.md`와 이 문서의 포트/URL 확인
- [ ] Backend dependency 설치 확인
- [ ] Frontend dependency 설치 확인
- [ ] `pytest` 통과 확인
- [ ] `npm run build` 통과 확인
- [x] secret/history regex scan 확인
- [ ] `/health` 응답 확인
- [ ] `/backends/ramulator2/status` 응답 확인
- [ ] 샘플 `Run` 실행 및 report 생성 확인
