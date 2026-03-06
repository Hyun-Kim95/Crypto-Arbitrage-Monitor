# 설치 및 실행 가이드

## 요구사항

- Python 3.9 이상
- Windows / macOS / Linux

## 1. 저장소 클론 또는 압축 해제

```bash
cd CryptoArbitrageMonitor
```

## 2. 가상환경 생성 (권장)

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. 의존성 설치

```bash
pip install -r requirements.txt
```

또는 패키지로 설치 (실행 시 `python -m crypto_arbitrage_monitor` 사용):

```bash
pip install -e .
```

## 4. 설정 (선택)

`.env.example`을 복사해 `.env`를 만들고 필요한 값만 수정합니다.

```bash
copy .env.example .env   # Windows
cp .env.example .env    # Linux/macOS
```

- `MIN_SPREAD_PERCENT`: 최소 수익률(%) — 이 값 이상일 때만 표시·알림 (기본 0.5)
- `MONITOR_SYMBOLS`: 모니터링할 코인 (쉼표 구분, 비우면 BTC/ETH/USDT)

## 5. 실행

프로젝트 루트에서:

```bash
# 패키지 설치한 경우
python -m crypto_arbitrage_monitor
```

- **기본**: 데스크톱 창이 열리며, 차익거래 기회가 테이블로 표시됩니다. 창을 닫으면 종료됩니다.
- **콘솔 모드**(터미널에만 출력):  
  **Windows:** `set USE_CONSOLE=1` 후 `python -m crypto_arbitrage_monitor`  
  **Linux/macOS:** `USE_CONSOLE=1 python -m crypto_arbitrage_monitor`  
  종료: **Ctrl+C**

`src`를 PYTHONPATH에 넣어 실행할 때:

**Windows (PowerShell):**
```powershell
$env:PYTHONPATH="src"; python -m crypto_arbitrage_monitor
```

**Linux / macOS:**
```bash
PYTHONPATH=src python -m crypto_arbitrage_monitor
```

## 6. 테스트 실행

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## 문제 해결

- **ModuleNotFoundError: crypto_arbitrage_monitor**  
  `pip install -e .` 또는 실행 시 `PYTHONPATH=src` 설정 후 실행하세요.

- **거래소 연결 실패**  
  네트워크/방화벽을 확인하고, 해당 거래소 API 상태를 확인하세요.


