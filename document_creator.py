import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class DocumentCreator:
    """구글 문서 자동 생성 클래스"""
    
    def __init__(self, credentials_path="token.json"):
        """
        초기화 함수
        
        Args:
            credentials_path (str): 인증 정보 파일 경로
        """
        self.credentials_path = credentials_path
        self.credentials = self._load_credentials()
        if self.credentials:
            self.docs_service = build("docs", "v1", credentials=self.credentials)
            self.drive_service = build("drive", "v3", credentials=self.credentials)
        else:
            self.docs_service = None
            self.drive_service = None
    
    def _load_credentials(self):
        """인증 정보 로드"""
        if not os.path.exists(self.credentials_path):
            return None
        
        with open(self.credentials_path, "r") as token:
            token_data = json.load(token)
        
        return Credentials.from_authorized_user_info(token_data)
    
    def is_authenticated(self):
        """인증 상태 확인"""
        return self.credentials is not None
    
    def create_document(self, title, content):
        """
        새 문서 생성
        
        Args:
            title (str): 문서 제목
            content (str): 문서 내용
            
        Returns:
            dict: 생성된 문서 정보 (id, url)
            None: 인증되지 않은 경우
        """
        if not self.is_authenticated():
            return None
        
        try:
            # 새 문서 생성
            document = self.drive_service.files().create(
                body={
                    "name": title,
                    "mimeType": "application/vnd.google-apps.document"
                }
            ).execute()
            
            doc_id = document.get("id")
            
            # 문서 내용 추가
            requests = [
                {
                    "insertText": {
                        "location": {
                            "index": 1
                        },
                        "text": content
                    }
                }
            ]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": requests}
            ).execute()
            
            document_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            
            return {
                "id": doc_id,
                "url": document_url
            }
            
        except Exception as e:
            print(f"문서 생성 중 오류 발생: {e}")
            return None
    
    def create_document_from_template(self, title, template_data):
        """
        템플릿을 기반으로 문서 생성
        
        Args:
            title (str): 문서 제목
            template_data (dict): 템플릿 데이터
            
        Returns:
            dict: 생성된 문서 정보 (id, url)
            None: 인증되지 않은 경우
        """
        if not self.is_authenticated():
            return None
        
        # 템플릿 기반 내용 생성
        content = self._format_template(template_data)
        
        return self.create_document(title, content)
    
    def _format_template(self, data):
        """
        템플릿 형식 지정
        
        Args:
            data (dict): 템플릿 데이터
            
        Returns:
            str: 형식이 지정된 문서 내용
        """
        # 여기에 템플릿 형식 지정 로직 구현
        # 예: 소프트웨어 구현 명세서 템플릿
        
        content = f"""# {data.get('title', '소프트웨어 구현 명세서')}

## 1. 요약
{data.get('summary', '')}

## 2. 요구사항 명세
### 2.1 기능 요구사항
{data.get('functional_requirements', '')}

### 2.2 비기능 요구사항
{data.get('non_functional_requirements', '')}

### 2.3 제약사항 및 가정
{data.get('constraints_assumptions', '')}

## 3. 시스템 아키텍처
### 3.1 아키텍처 개요
{data.get('architecture_overview', '')}

### 3.2 시스템 구성요소
{data.get('system_components', '')}

## 4. 기술 스택
### 4.1 개발 환경
{data.get('development_environment', '')}

### 4.2 백엔드 기술
{data.get('backend_technology', '')}

### 4.3 프론트엔드 기술
{data.get('frontend_technology', '')}

### 4.4 인프라 및 배포
{data.get('infrastructure_deployment', '')}

## 5. 데이터 모델
### 5.1 엔티티 관계 다이어그램
{data.get('entity_relationship_diagram', '')}

### 5.2 데이터베이스 스키마
{data.get('database_schema', '')}

### 5.3 데이터 흐름
{data.get('data_flow', '')}

## 6. API 명세
### 6.1 API 개요
{data.get('api_overview', '')}

### 6.2 엔드포인트 상세
{data.get('endpoint_details', '')}

## 7. 상세 컴포넌트 설계
### 7.1 백엔드 컴포넌트
{data.get('backend_components', '')}

### 7.2 프론트엔드 컴포넌트
{data.get('frontend_components', '')}

### 7.3 핵심 알고리즘 및 로직
{data.get('core_algorithms_logic', '')}

## 8. 보안 설계
### 8.1 보안 위협 분석
{data.get('security_threat_analysis', '')}

### 8.2 보안 통제
{data.get('security_controls', '')}

## 9. 테스트 전략
### 9.1 테스트 접근법
{data.get('test_approach', '')}

### 9.2 테스트 케이스
{data.get('test_cases', '')}

## 10. 구현 로드맵
### 10.1 개발 단계
{data.get('development_phases', '')}

## 11. 개발 가이드라인
### 11.1 개발 표준
{data.get('development_standards', '')}

### 11.2 문서화 요구사항
{data.get('documentation_requirements', '')}

## 12. 부록
### 12.1 용어 설명
{data.get('glossary', '')}

### 12.2 참조 문서
{data.get('reference_documents', '')}

## 13. 구현 완료 상태 평가
### 13.1 요구사항 구현 검증
{data.get('requirements_implementation_verification', '')}

### 13.2 구현 상태 결론
{data.get('implementation_status_conclusion', '')}
"""
        return content 