# Crypto Arbitrage Monitor

국내·해외 암호화폐 거래소 간 **현물 가격 차이(스프레드)**를 실시간으로 감지하여 차익거래 기회를 알려주는 모니터링 프로그램입니다.  
자동 매매가 아닌 **정보 제공** 목적입니다.

## 지원 거래소

- **국내**: 업비트, 빗썸  
- **해외**: Binance, Bybit, Gate.io  

## 주요 기능

- 실시간 호가(매수 1호가/매도 1호가) 수집 (WebSocket)
- 거래소 간 스프레드(%) 자동 계산
- 최소 수익률·코인 필터
- 알림: 소리

## 요구사항

- Python 3.10+

## 설치 및 실행

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# 의존성 설치
pip install -r requirements.txt

# 설정 (선택)
copy .env.example .env
# .env 편집

# 실행 — 데스크톱 창으로 실행 (기본)
python -m crypto_arbitrage_monitor
```

- **데스크톱 GUI**(기본): 실행 시 모니터링 창이 열립니다. 창을 닫으면 종료됩니다.
- **콘솔 모드**: 터미널에서 테이블 출력만 사용하려면 `USE_CONSOLE=1` 로 실행하세요.  
  `set USE_CONSOLE=1` (Windows) / `USE_CONSOLE=1 python -m crypto_arbitrage_monitor` (Linux/macOS)

## 프로젝트 구조

```
src/crypto_arbitrage_monitor/
  __init__.py
  config.py           # 설정
  logging_config.py   # 로깅
  models.py           # 데이터 모델
  exchanges/          # 거래소 WebSocket
  spread/             # 스프레드 계산
  alerts/             # 알림
  ui/                 # UI (데스크톱 + 콘솔)
```

## 라이선스

MIT
