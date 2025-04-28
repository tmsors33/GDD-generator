# Google Drive Document Generator (GDD)

구글 드라이브 문서 자동 생성기는 사용자가 입력한 내용을 바탕으로 소프트웨어 구현 명세서 등 다양한 문서를 구글 드라이브에 자동으로 생성해주는 웹 애플리케이션입니다.

## 주요 기능

- 텍스트 입력을 분석하여 소프트웨어 구현 명세서 자동 생성
- OpenAI를 활용한 문서 템플릿 구성
- 구글 드라이브 문서 자동 생성 및 관리
- 기존 문서를 시스템에 학습시켜 템플릿 품질 향상

## 기술 스택

- **백엔드**: FastAPI, Python 3.9+
- **프론트엔드**: HTML, CSS, JavaScript
- **인증**: Google OAuth 2.0
- **데이터베이스**: ChromaDB (벡터 데이터베이스)
- **AI**: OpenAI API (GPT 모델)
- **배포**: Vercel

## 코드 최적화

GDD는 필요에 따라 무거운 라이브러리를 지연 로드하는 방식으로 최적화되어 있습니다:

1. **지연 로드 패턴**: 필요한 시점에만 무거운 모듈을 로드하여 메모리 사용량 최소화
   - Google API 관련 모듈
   - OpenAI 모듈
   - 문서 학습 관련 모듈

2. **모듈화된 설계**: 각 기능을 독립적인 클래스로 분리
   - `TemplateHandler`: 문서 템플릿 처리
   - `DocumentCreator`: 구글 문서 생성 및 관리
   - `DocumentLearner`: 문서 학습 및 벡터 저장소 관리

3. **효율적인 에러 처리**: 예외 상황에 대한 체계적인 처리

## 설치 및 실행

### 필수 요구사항

- Python 3.9 이상
- Google 계정 및 API 접근 권한

### 환경 설정

1. 저장소 복제:
```bash
git clone https://github.com/yourusername/gdd.git
cd gdd
```

2. 가상 환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치:
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정:
`.env.example`을 `.env`로 복사하고 필요한 값 설정:
```
OPENAI_API_KEY=your_openai_api_key
CLIENT_ID=your_google_client_id
CLIENT_SECRET=your_google_client_secret
REDIRECT_URI=http://localhost:8000/callback
SCOPES=https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/drive.file
```

### 실행

```bash
python app.py
```

애플리케이션이 `http://localhost:8000`에서 실행됩니다.

## 사용 방법

1. 웹 브라우저에서 `http://localhost:8000` 접속
2. Google 계정으로 로그인
3. 문서 생성 페이지에서 원하는 문서 내용 입력
4. "문서 생성하기" 버튼 클릭
5. 생성된 문서 링크로 이동

## 문서 학습 기능

기존 문서를 시스템에 학습시켜 템플릿 품질을 향상시킬 수 있습니다:

1. "문서 학습" 페이지로 이동
2. 파일 업로드 또는 텍스트 직접 입력
3. 카테고리 및 태그 설정
4. "문서 업로드 및 학습" 또는 "텍스트 학습" 버튼 클릭

## API 엔드포인트

- `GET /`: 메인 페이지
- `GET /login`: Google 로그인
- `GET /callback`: OAuth 콜백 처리
- `POST /create-document`: 문서 생성
- `GET /learn`: 문서 학습 페이지
- `POST /upload-document`: 문서 파일 업로드 및 학습
- `POST /learn-text`: 텍스트 학습
- `POST /clear-learned-data`: 학습 데이터 삭제
- `GET /about`: 소개 페이지
- `GET /api/login-status`: 로그인 상태 확인
- `GET /logout`: 로그아웃

## 라이센스

MIT License

## 기여 방법

1. 프로젝트 포크
2. 새 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시 (`git push origin feature/amazing-feature`)
5. Pull Request 생성 