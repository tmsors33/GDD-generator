import os
import json
from typing import Optional, List
from fastapi import FastAPI, Request, Form, Depends, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2AuthorizationCodeBearer
import uvicorn
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

# 사용자 정의 모듈 임포트
from document_creator import DocumentCreator
from template_handler import TemplateHandler
from document_learner import DocumentLearner

# 환경 변수 로드
load_dotenv()

app = FastAPI(title="구글 드라이브 문서 자동 생성기")

# 디렉토리 생성 (Vercel 환경을 위한 수정)
for directory in ["templates", "static", "static/css", "static/js", "chroma_db"]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# 템플릿 및 정적 파일 설정
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# OAuth 설정
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES", "").split(",")

# 토큰 저장 - Vercel에서는 임시 저장소 사용
TOKEN_FILE = "token.json"
if os.getenv("VERCEL_ENV"):
    # Vercel 환경에서는 /tmp 디렉토리 사용
    TOKEN_FILE = "/tmp/token.json"

# 템플릿 처리기 및 문서 생성기 초기화
template_handler = TemplateHandler()
document_creator = DocumentCreator(TOKEN_FILE)
document_learner = DocumentLearner(persist_directory="/tmp/chroma_db" if os.getenv("VERCEL_ENV") else "chroma_db")

def create_flow():
    """OAuth 인증 흐름 생성"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    return flow

def get_credentials():
    """저장된 토큰에서 사용자 인증 정보 가져오기"""
    if not os.path.exists(TOKEN_FILE):
        return None
    
    with open(TOKEN_FILE, "r") as token:
        token_data = json.load(token)
    
    return Credentials.from_authorized_user_info(token_data)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login():
    """구글 로그인 페이지로 리다이렉트"""
    flow = create_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    return RedirectResponse(authorization_url)

@app.get("/callback")
async def callback(request: Request, code: Optional[str] = None):
    """OAuth 콜백 처리"""
    if not code:
        raise HTTPException(status_code=400, detail="인증 코드가 제공되지 않았습니다.")
    
    flow = create_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # 토큰 저장
    with open(TOKEN_FILE, "w") as token:
        token.write(credentials.to_json())
    
    return RedirectResponse("/")

@app.post("/create-document")
async def create_document(
    request: Request, 
    document_title: str = Form(...), 
    document_content: str = Form(...),
    use_learned_data: Optional[str] = Form(None)
):
    """구글 독스 문서 생성"""
    # 인증 확인
    credentials = get_credentials()
    if not credentials:
        return RedirectResponse("/login")
    
    # 문서 생성기 초기화
    document_creator = DocumentCreator(TOKEN_FILE)
    
    # 학습된 데이터 사용 여부 확인
    use_learned = use_learned_data == "true"
    template_data = {}
    reference_count = 0
    
    if use_learned and document_learner.vectorstore:
        # 학습된 데이터 기반 템플릿 생성
        template_data = document_learner.generate_template_from_query(document_content)
        
        # 참조된 문서 있는 경우
        if template_data:
            reference_docs = document_learner.search_similar_documents(document_content)
            reference_count = len(reference_docs)
    
    # 학습된 데이터가 없거나 사용하지 않는 경우
    if not template_data:
        template_data = template_handler.parse_user_input(document_content)
    
    # 템플릿을 기반으로 문서 생성
    result = document_creator.create_document_from_template(document_title, template_data)
    
    if result:
        return templates.TemplateResponse(
            "success.html", 
            {
                "request": request, 
                "document_url": result["url"], 
                "document_title": document_title,
                "used_learned_data": use_learned and reference_count > 0,
                "reference_count": reference_count
            }
        )
    else:
        raise HTTPException(status_code=500, detail="문서 생성 중 오류가 발생했습니다.")

@app.get("/learn", response_class=HTMLResponse)
async def learn_page(request: Request):
    """문서 학습 페이지"""
    return templates.TemplateResponse("learn.html", {"request": request})

@app.post("/upload-document")
async def upload_document(
    request: Request,
    document_file: UploadFile = File(...),
    document_category: str = Form(...),
    document_tags: Optional[str] = Form(None)
):
    """문서 파일 업로드 및 학습"""
    # 임시 파일로 저장
    file_path = f"temp_{document_file.filename}"
    
    try:
        # 메타데이터 준비
        metadata = {"category": document_category}
        if document_tags:
            metadata["tags"] = document_tags
        
        # 파일 임시 저장
        with open(file_path, "wb") as temp_file:
            content = await document_file.read()
            temp_file.write(content)
        
        # 문서 학습
        documents = document_learner.process_document(file_path, metadata)
        success = document_learner.add_documents(documents)
        
        # 임시 파일 삭제
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if success:
            return templates.TemplateResponse(
                "learn_success.html", 
                {
                    "request": request,
                    "chunks_count": len(documents),
                    "category": document_category,
                    "tags": document_tags
                }
            )
        else:
            raise HTTPException(status_code=500, detail="문서 학습 중 오류가 발생했습니다.")
            
    except Exception as e:
        # 오류 발생 시 임시 파일 삭제
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"문서 처리 중 오류 발생: {str(e)}")

@app.post("/learn-text")
async def learn_text(
    request: Request,
    document_text: str = Form(...),
    text_category: str = Form(...),
    text_tags: Optional[str] = Form(None)
):
    """텍스트 직접 입력하여 학습"""
    try:
        # 메타데이터 준비
        metadata = {"category": text_category}
        if text_tags:
            metadata["tags"] = text_tags
        
        # 텍스트 학습
        success = document_learner.learn_from_text(document_text, metadata)
        
        if success:
            # 대략적인 청크 수 계산 (평균 1000자당 1청크)
            approx_chunks = max(1, len(document_text) // 1000)
            
            return templates.TemplateResponse(
                "learn_success.html", 
                {
                    "request": request,
                    "chunks_count": approx_chunks,
                    "category": text_category,
                    "tags": text_tags
                }
            )
        else:
            raise HTTPException(status_code=500, detail="텍스트 학습 중 오류가 발생했습니다.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"텍스트 처리 중 오류 발생: {str(e)}")

@app.post("/clear-learned-data")
async def clear_learned_data(request: Request):
    """학습된 데이터 모두 삭제"""
    success = document_learner.clear_vectorstore()
    
    if success:
        return RedirectResponse("/learn", status_code=303)
    else:
        raise HTTPException(status_code=500, detail="데이터 삭제 중 오류가 발생했습니다.")

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """소개 페이지"""
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/api/login-status")
async def login_status():
    """로그인 상태 확인 API"""
    credentials = get_credentials()
    return JSONResponse({"loggedIn": credentials is not None})

@app.get("/logout")
async def logout():
    """로그아웃 및 토큰 삭제"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    return RedirectResponse("/")

if __name__ == "__main__":
    # 애플리케이션 실행
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True) 