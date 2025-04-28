import os
import tempfile
from typing import List, Dict, Any, Optional
import json
import shutil
import importlib
import warnings

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# 필수적인 기본 모듈만 먼저 로드
import openai

class DocumentLearner:
    """사용자 문서 학습 및 벡터 저장소 생성 클래스"""

    def __init__(self, api_key=None, persist_directory="chroma_db"):
        """
        초기화 함수
        
        Args:
            api_key (str, optional): OpenAI API 키 (없으면 환경 변수에서 로드)
            persist_directory (str): 벡터 저장소 디렉토리 경로
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.persist_directory = persist_directory
        self.vectorstore = None
        self.embedding = None
        
        # 벡터 저장소 디렉토리 생성
        if not os.path.exists(self.persist_directory):
            try:
                os.makedirs(self.persist_directory, exist_ok=True)
            except:
                # Vercel 환경에서는 /tmp 디렉토리 사용
                self.persist_directory = "/tmp/chroma_db"
                os.makedirs(self.persist_directory, exist_ok=True)
        
        if self.api_key:
            openai.api_key = self.api_key
            
            # 벡터 저장소 초기화는 필요할 때만 수행하기 위해 지연시킵니다
            try:
                self._initialize_if_needed()
            except Exception as e:
                print(f"벡터 저장소 초기화 중 오류 발생: {e}")
    
    def _initialize_if_needed(self):
        """필요할 때만 무거운 모듈을 임포트하고 초기화합니다"""
        if self.embedding is None and self.api_key:
            try:
                # 동적으로 필요한 모듈 임포트
                from langchain.embeddings import OpenAIEmbeddings
                self.embedding = OpenAIEmbeddings(
                    openai_api_key=self.api_key,
                    model="text-embedding-ada-002"
                )
                
                # 기존 벡터 저장소 로드 시도
                if os.path.exists(self.persist_directory):
                    try:
                        from langchain.vectorstores import Chroma
                        self.vectorstore = Chroma(
                            persist_directory=self.persist_directory, 
                            embedding_function=self.embedding
                        )
                    except Exception as e:
                        print(f"벡터 저장소 로드 중 오류 발생: {e}")
                        self.vectorstore = None
            except ImportError as e:
                warnings.warn(f"필요한 패키지가 설치되어 있지 않습니다: {e}. 이 기능은 사용할 수 없습니다.")
                self.embedding = None
                self.vectorstore = None
    
    def process_document(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        문서 파일을 처리하여 Document 객체 목록 반환
        
        Args:
            file_path (str): 처리할 문서 파일 경로
            metadata (Dict, optional): 문서에 추가할 메타데이터
            
        Returns:
            List[Document]: 처리된 문서 목록
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        # 간소화된 문서 처리 로직
        try:
            # 텍스트 파일로 간주하고 직접 처리
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            
            # 문서 생성
            from langchain.schema import Document
            doc = Document(page_content=text, metadata=metadata or {})
            
            # 텍스트 분할
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
            
            return text_splitter.split_documents([doc])
            
        except Exception as e:
            print(f"간단한 텍스트 처리 중 오류 발생: {e}")
            print("고급 문서 로더 사용 시도 중...")
            
            # 대체 로직: 확장자별 적절한 로더 사용
            try:
                file_ext = os.path.splitext(file_path)[1].lower()
                
                if file_ext == '.txt':
                    from langchain.document_loaders import TextLoader
                    loader = TextLoader(file_path, encoding='utf-8')
                elif file_ext == '.pdf':
                    try:
                        from langchain.document_loaders import PyPDFLoader
                        loader = PyPDFLoader(file_path)
                    except:
                        print("PyPDFLoader를 사용할 수 없습니다. 대안 사용...")
                        with open(file_path, 'rb') as f:
                            text = str(f.read())
                        from langchain.schema import Document
                        doc = Document(page_content=text, metadata=metadata or {})
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=1000, 
                            chunk_overlap=200,
                            length_function=len,
                        )
                        return text_splitter.split_documents([doc])
                else:
                    # 기본 처리: 바이너리로 읽어서 텍스트로 변환 시도
                    with open(file_path, 'rb') as f:
                        text = str(f.read())
                    from langchain.schema import Document
                    doc = Document(page_content=text, metadata=metadata or {})
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000, 
                        chunk_overlap=200,
                        length_function=len,
                    )
                    return text_splitter.split_documents([doc])
                
                # 로더를 사용한 문서 로드
                documents = loader.load()
                
                # 메타데이터 추가
                if metadata:
                    for doc in documents:
                        doc.metadata.update(metadata)
                
                # 텍스트 분할
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len,
                )
                
                return text_splitter.split_documents(documents)
                
            except Exception as e:
                print(f"고급 문서 처리 중 오류 발생: {e}")
                
                # 최후의 방법: 모든 예외 처리 후 단순히 파일 내용을 텍스트로 읽기
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    text = str(content)
                    
                    # 짧은 더미 문서 생성
                    from langchain.schema import Document
                    doc = Document(
                        page_content=f"파일 이름: {os.path.basename(file_path)}\n처리 실패: 파일 형식이 지원되지 않습니다.",
                        metadata=metadata or {}
                    )
                    return [doc]
                except:
                    raise ValueError("파일을 처리할 수 없습니다. 지원되는 형식인지 확인하세요.")
    
    def add_documents(self, documents: List[Any]) -> bool:
        """
        문서를 벡터 저장소에 추가
        
        Args:
            documents (List[Document]): 추가할 문서 목록
            
        Returns:
            bool: 성공 여부
        """
        # 벡터 저장소 초기화
        self._initialize_if_needed()
        
        if not self.embedding:
            return False
        
        try:
            # 벡터 저장소가 없으면 생성
            if self.vectorstore is None:
                from langchain.vectorstores import Chroma
                self.vectorstore = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embedding,
                    persist_directory=self.persist_directory
                )
            else:
                # 기존 벡터 저장소에 문서 추가
                self.vectorstore.add_documents(documents)
            
            # 변경사항 저장
            self.vectorstore.persist()
            return True
        
        except Exception as e:
            print(f"문서 추가 중 오류 발생: {e}")
            return False
    
    def learn_from_file(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        파일에서 문서를 학습
        
        Args:
            file_path (str): 학습할 문서 파일 경로
            metadata (Dict, optional): 문서에 추가할 메타데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 문서 처리
            documents = self.process_document(file_path, metadata)
            
            # 벡터 저장소에 추가
            return self.add_documents(documents)
        
        except Exception as e:
            print(f"파일 학습 중 오류 발생: {e}")
            return False
    
    def learn_from_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        텍스트에서 문서를 학습
        
        Args:
            text (str): 학습할 텍스트
            metadata (Dict, optional): 문서에 추가할 메타데이터
            
        Returns:
            bool: 성공 여부
        """
        try:
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
                tmp.write(text)
                tmp_path = tmp.name
            
            # 텍스트 파일 학습
            documents = self.process_document(tmp_path, metadata)
            result = self.add_documents(documents) if documents else False
            
            # 임시 파일 삭제
            os.unlink(tmp_path)
            
            return result
        
        except Exception as e:
            print(f"텍스트 학습 중 오류 발생: {e}")
            return False
    
    def search_similar_documents(self, query: str, top_k: int = 5) -> List[Any]:
        """
        쿼리와 유사한 문서 검색
        
        Args:
            query (str): 검색 쿼리
            top_k (int): 반환할 문서 수
            
        Returns:
            List[Document]: 검색된 문서 목록
        """
        # 벡터 저장소 초기화
        self._initialize_if_needed()
        
        if not self.vectorstore:
            return []
        
        try:
            documents = self.vectorstore.similarity_search(query, k=top_k)
            return documents
        
        except Exception as e:
            print(f"유사 문서 검색 중 오류 발생: {e}")
            return []
    
    def generate_template_from_query(self, query: str) -> Dict[str, Any]:
        """
        쿼리와 유사한 문서를 기반으로 템플릿 데이터 생성
        
        Args:
            query (str): 검색 쿼리
            
        Returns:
            Dict[str, Any]: 템플릿 데이터
        """
        # 간소화된 구현: Vercel 배포를 위해 단순화됨
        # 실제 벡터 검색 대신 OpenAI API만 사용하여 템플릿 생성
        if not self.api_key:
            return {}
        
        try:
            # OpenAI API를 사용하여 템플릿 데이터 생성
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 소프트웨어 구현 명세서 작성을 도와주는 전문가입니다. 사용자 입력을 분석하여 소프트웨어 구현 명세서의 각 섹션별 내용을 JSON 형식으로 구성해주세요."},
                    {"role": "user", "content": f"사용자 입력: {query}"}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"템플릿 데이터 생성 중 오류 발생: {e}")
            return {}
    
    def clear_vectorstore(self) -> bool:
        """
        벡터 저장소 초기화
        
        Returns:
            bool: 성공 여부
        """
        try:
            if os.path.exists(self.persist_directory):
                shutil.rmtree(self.persist_directory)
            
            self.vectorstore = None
            return True
            
        except Exception as e:
            print(f"벡터 저장소 초기화 중 오류 발생: {e}")
            return False 