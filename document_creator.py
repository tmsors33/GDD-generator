import os
import json
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# 필요시에만 Google APIs 임포트
googleapiclient = None
google_auth = None
google_auth_oauthlib = None
google_auth_httplib2 = None

class DocumentCreator:
    """Google Docs 문서 생성 및 관리 클래스"""
    
    def __init__(self, token_file, credentials_file=None):
        """
        초기화 함수
        
        Args:
            token_file (str): 토큰 파일 경로
            credentials_file (str, optional): 자격 증명 파일 경로
        """
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.service = None
        self.creds = None
    
    def _initialize_google_apis(self):
        """Google APIs 동적 로드 및 초기화"""
        global googleapiclient, google_auth, google_auth_oauthlib, google_auth_httplib2
        
        if googleapiclient is None:
            # 필요한 Google APIs 모듈 동적 로드
            import googleapiclient.discovery
            import google.auth
            import google.auth.transport.requests
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import google_auth_httplib2
            
            # 전역 변수에 할당
            googleapiclient = googleapiclient
            google_auth = google.auth
            google_auth_oauthlib = google_auth_oauthlib
            google_auth_httplib2 = google_auth_httplib2
    
    def authenticate(self, scopes):
        """
        Google API 인증
        
        Args:
            scopes (list): 인증 범위
            
        Returns:
            bool: 인증 성공 여부
        """
        self._initialize_google_apis()
        
        try:
            creds = None
            # 기존 토큰 파일에서 자격 증명 로드
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as token:
                    token_data = json.load(token)
                    # Vercel에서는 token_data에서 직접 자격 증명 생성
                    if os.environ.get('VERCEL_ENV'):
                        from google.oauth2.credentials import Credentials
                        creds = Credentials.from_authorized_user_info(token_data)
                    else:
                        from google.oauth2.credentials import Credentials
                        creds = Credentials.from_authorized_user_info(token_data, scopes)
            
            # 자격 증명이 없거나 유효하지 않은 경우 새로 인증
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # 토큰 갱신
                    creds.refresh(Request())
                elif self.credentials_file:
                    # 새 인증 흐름 시작
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, scopes)
                    creds = flow.run_local_server(port=0)
                else:
                    return False
                
                # 토큰 저장
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.creds = creds
            # Google Docs API 서비스 초기화
            self.service = googleapiclient.discovery.build('docs', 'v1', credentials=creds)
            return True
        
        except Exception as e:
            print(f"인증 중 오류 발생: {e}")
            return False
    
    def create_document(self, title):
        """
        새 문서 생성
        
        Args:
            title (str): 문서 제목
            
        Returns:
            str: 생성된 문서 ID
        """
        if not self.service:
            raise RuntimeError("API 서비스가 초기화되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        try:
            document = self.service.documents().create(body={'title': title}).execute()
            print(f'문서가 생성되었습니다: {document.get("title")}')
            return document.get('documentId')
        except Exception as e:
            print(f"문서 생성 중 오류 발생: {e}")
            return None
    
    def update_document(self, document_id, updates):
        """
        문서 내용 업데이트
        
        Args:
            document_id (str): 문서 ID
            updates (list): 업데이트 요청 목록
            
        Returns:
            bool: 업데이트 성공 여부
        """
        if not self.service:
            raise RuntimeError("API 서비스가 초기화되지 않았습니다. authenticate()를 먼저 호출하세요.")
        
        try:
            result = self.service.documents().batchUpdate(
                documentId=document_id, body={'requests': updates}).execute()
            return True
        except Exception as e:
            print(f"문서 업데이트 중 오류 발생: {e}")
            return False
    
    def get_document_link(self, document_id):
        """
        문서 링크 생성
        
        Args:
            document_id (str): 문서 ID
            
        Returns:
            str: 문서 링크
        """
        return f"https://docs.google.com/document/d/{document_id}/edit"
        
    def create_document_from_template(self, title, template_data):
        """
        템플릿을 기반으로 문서 생성
        
        Args:
            title (str): 문서 제목
            template_data (dict): 템플릿 데이터
            
        Returns:
            dict: 생성된 문서 정보 (id, url)
            None: 인증 또는 생성 실패 시
        """
        # Google API 인증
        if not self.service:
            scopes = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.file']
            success = self.authenticate(scopes)
            if not success:
                print("Google API 인증에 실패했습니다.")
                return None
        
        try:
            # 빈 문서 생성
            doc_id = self.create_document(title)
            if not doc_id:
                return None
            
            # 템플릿 데이터 기반 문서 내용 생성
            content = self._format_template_to_doc(template_data)
            
            # 문서 내용 업데이트
            success = self.update_document(doc_id, content)
            if not success:
                return None
            
            # 문서 URL 생성
            doc_url = self.get_document_link(doc_id)
            
            return {
                "id": doc_id,
                "url": doc_url
            }
            
        except Exception as e:
            print(f"템플릿 기반 문서 생성 중 오류 발생: {e}")
            return None
    
    def _format_template_to_doc(self, data):
        """
        템플릿 데이터를 Google Docs 업데이트 요청으로 변환
        
        Args:
            data (dict): 템플릿 데이터
            
        Returns:
            list: Google Docs 업데이트 요청 목록
        """
        requests = []
        current_index = 1
        
        # 문서 제목 삽입
        title = data.get('title', '소프트웨어 구현 명세서')
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': f"# {title}\n\n"
            }
        })
        current_index += len(f"# {title}\n\n")
        
        # 각 섹션 삽입
        sections = [
            ('summary', '## 1. 요약'),
            ('functional_requirements', '### 2.1 기능 요구사항'),
            ('non_functional_requirements', '### 2.2 비기능 요구사항'),
            ('constraints_assumptions', '### 2.3 제약사항 및 가정'),
            ('architecture_overview', '### 3.1 아키텍처 개요'),
            ('system_components', '### 3.2 시스템 구성요소'),
            ('development_environment', '### 4.1 개발 환경'),
            ('backend_technology', '### 4.2 백엔드 기술'),
            ('frontend_technology', '### 4.3 프론트엔드 기술'),
            ('infrastructure_deployment', '### 4.4 인프라 및 배포'),
            ('entity_relationship_diagram', '### 5.1 엔티티 관계 다이어그램'),
            ('database_schema', '### 5.2 데이터베이스 스키마'),
            ('data_flow', '### 5.3 데이터 흐름'),
            ('api_overview', '### 6.1 API 개요'),
            ('endpoint_details', '### 6.2 엔드포인트 상세'),
            ('backend_components', '### 7.1 백엔드 컴포넌트'),
            ('frontend_components', '### 7.2 프론트엔드 컴포넌트'),
            ('core_algorithms_logic', '### 7.3 핵심 알고리즘 및 로직'),
            ('security_threat_analysis', '### 8.1 보안 위협 분석'),
            ('security_controls', '### 8.2 보안 통제'),
            ('test_approach', '### 9.1 테스트 접근법'),
            ('test_cases', '### 9.2 테스트 케이스'),
            ('development_phases', '### 10.1 개발 단계'),
            ('development_standards', '### 11.1 개발 표준'),
            ('documentation_requirements', '### 11.2 문서화 요구사항'),
            ('glossary', '### 12.1 용어 설명'),
            ('reference_documents', '### 12.2 참조 문서'),
            ('requirements_implementation_verification', '### 13.1 요구사항 구현 검증'),
            ('implementation_status_conclusion', '### 13.2 구현 상태 결론')
        ]
        
        for key, header in sections:
            content = data.get(key, '')
            section_text = f"{header}\n{content}\n\n"
            requests.append({
                'insertText': {
                    'location': {'index': current_index},
                    'text': section_text
                }
            })
            current_index += len(section_text)
        
        # 스타일 적용 (제목)
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': 1,
                    'endIndex': len(f"# {title}") + 1
                },
                'paragraphStyle': {
                    'namedStyleType': 'TITLE',
                    'alignment': 'CENTER'
                },
                'fields': 'namedStyleType,alignment'
            }
        })
        
        return requests 