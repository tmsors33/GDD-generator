import re
import os
import json
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 필요시에만 OpenAI 임포트
openai = None

class TemplateHandler:
    """문서 템플릿 처리 클래스"""
    
    def __init__(self, api_key=None):
        """
        초기화 함수
        
        Args:
            api_key (str, optional): OpenAI API 키 (없으면 환경 변수에서 로드)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
    
    def parse_user_input(self, user_input):
        """
        사용자 입력 파싱
        
        Args:
            user_input (str): 사용자 입력
            
        Returns:
            dict: 파싱된 템플릿 데이터
        """
        # OpenAI API를 사용하여 사용자 입력을 템플릿 데이터로 변환
        try:
            if self.api_key:
                return self._generate_template_data_with_ai(user_input)
            else:
                return self._basic_parsing(user_input)
        except Exception as e:
            print(f"입력 파싱 중 오류 발생: {e}")
            return self._default_template_data()
    
    def _generate_template_data_with_ai(self, user_input):
        """
        AI를 사용하여 템플릿 데이터 생성
        
        Args:
            user_input (str): 사용자 입력
            
        Returns:
            dict: 템플릿 데이터
        """
        try:
            # 필요시에만 OpenAI 모듈 로드
            global openai
            if openai is None:
                import openai
                openai.api_key = self.api_key
                
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 소프트웨어 구현 명세서 작성을 도와주는 전문가입니다. 사용자 입력을 분석하여 소프트웨어 구현 명세서의 각 섹션별 내용을 JSON 형식으로 구성해주세요."},
                    {"role": "user", "content": user_input}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # 기본 템플릿 데이터와 병합
            default_data = self._default_template_data()
            for key in default_data:
                if key not in data or not data[key]:
                    data[key] = default_data[key]
            
            return data
            
        except Exception as e:
            print(f"AI를 사용한 템플릿 데이터 생성 중 오류 발생: {e}")
            return self._default_template_data()
    
    def _basic_parsing(self, user_input):
        """
        기본 파싱 (OpenAI API 없을 때)
        
        Args:
            user_input (str): 사용자 입력
            
        Returns:
            dict: 파싱된 템플릿 데이터
        """
        # 간단한 규칙 기반 파싱
        data = self._default_template_data()
        
        # 소프트웨어 타이틀 추출
        title_match = re.search(r"(제목|타이틀|이름|소프트웨어명)[\s:]*([^\n]+)", user_input)
        if title_match:
            data["title"] = title_match.group(2).strip()
        
        # 요약 추출
        summary_match = re.search(r"(요약|개요)[\s:]*([^\n]+(?:\n[^\n#]+)*)", user_input)
        if summary_match:
            data["summary"] = summary_match.group(2).strip()
        
        # 기능 요구사항 추출
        func_req_match = re.search(r"(기능[ ]?요구사항|주요[ ]?기능)[\s:]*([^\n]+(?:\n[^\n#]+)*)", user_input)
        if func_req_match:
            data["functional_requirements"] = func_req_match.group(2).strip()
        
        return data
    
    def _default_template_data(self):
        """
        기본 템플릿 데이터
        
        Returns:
            dict: 기본 템플릿 데이터
        """
        return {
            "title": "소프트웨어 구현 명세서",
            "summary": "이 문서는 소프트웨어의 주요 기능과 구현 방법을 설명합니다.",
            "functional_requirements": "- 주요 기능 1\n- 주요 기능 2\n- 주요 기능 3",
            "non_functional_requirements": "- 성능 요구사항\n- 보안 요구사항\n- 사용성 요구사항",
            "constraints_assumptions": "- 개발 환경 제약사항\n- 주요 가정사항",
            "architecture_overview": "시스템 아키텍처에 대한 설명과 주요 구성요소간의 관계를 설명합니다.",
            "system_components": "- 구성요소 1: 역할 및 책임\n- 구성요소 2: 역할 및 책임",
            "development_environment": "- 개발 언어 및 프레임워크\n- 개발 도구",
            "backend_technology": "백엔드에 사용되는 주요 기술과 프레임워크를 설명합니다.",
            "frontend_technology": "프론트엔드에 사용되는 주요 기술과 프레임워크를 설명합니다.",
            "infrastructure_deployment": "인프라 구조와 배포 방법을 설명합니다.",
            "entity_relationship_diagram": "주요 엔티티 간의 관계를 설명합니다.",
            "database_schema": "데이터베이스 스키마와 테이블 구조를 설명합니다.",
            "data_flow": "시스템 내 데이터 흐름을 설명합니다.",
            "api_overview": "API 설계 원칙과 인증 메커니즘을 설명합니다.",
            "endpoint_details": "주요 API 엔드포인트와 메서드를 설명합니다.",
            "backend_components": "백엔드 주요 모듈과 클래스 설계를 설명합니다.",
            "frontend_components": "프론트엔드 컴포넌트 계층 구조와 상태 관리 방법을 설명합니다.",
            "core_algorithms_logic": "핵심 알고리즘과 비즈니스 로직을 설명합니다.",
            "security_threat_analysis": "주요 보안 위협과 리스크를 분석합니다.",
            "security_controls": "인증 및 권한 부여 메커니즘, 데이터 보호 전략을 설명합니다.",
            "test_approach": "테스트 수준 및 유형, 테스트 환경, 자동화 전략을 설명합니다.",
            "test_cases": "주요 테스트 시나리오와 데이터 요구사항을 설명합니다.",
            "development_phases": "주요 개발 단계와 마일스톤을 설명합니다.",
            "development_standards": "설계 원칙 및 패턴, 명명 규칙, 구조화 방법론을 설명합니다.",
            "documentation_requirements": "코드 주석 요구사항, 기술 문서 작성 지침을 설명합니다.",
            "glossary": "주요 기술 및 비즈니스 용어 정의를 설명합니다.",
            "reference_documents": "관련 문서 및 리소스 목록을 포함합니다.",
            "requirements_implementation_verification": "모든 기능 요구사항 구현 검증, 비기능 요구사항 충족 검증, 미해결 이슈 및 제약사항 목록을 설명합니다.",
            "implementation_status_conclusion": "구현 완료 상태: [COMPLETE / CONTINUE]\n\n완료되지 않은 항목 목록 (해당되는 경우)\n\n다음 단계 권장사항 (해당되는 경우)"
        } 