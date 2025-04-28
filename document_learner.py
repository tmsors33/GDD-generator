import os
import tempfile
from typing import List, Dict, Any, Optional
import json
import shutil

import openai
from langchain.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader, 
    UnstructuredExcelLoader
)
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

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
            self.embedding = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                model="text-embedding-ada-002"
            )
            
            # 기존 벡터 저장소 로드 또는 생성
            if os.path.exists(self.persist_directory):
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory, 
                    embedding_function=self.embedding
                )
            else:
                self.vectorstore = None
        else:
            self.embedding = None
            self.vectorstore = None
    
    def process_document(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
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
        
        # 파일 확장자에 따른 적절한 로더 선택
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            loader = PyPDFLoader(file_path)
        elif file_ext == '.txt':
            loader = TextLoader(file_path)
        elif file_ext in ['.docx', '.doc']:
            loader = Docx2txtLoader(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            loader = UnstructuredExcelLoader(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_ext}")
        
        # 문서 로드
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
    
    def add_documents(self, documents: List[Document]) -> bool:
        """
        문서를 벡터 저장소에 추가
        
        Args:
            documents (List[Document]): 추가할 문서 목록
            
        Returns:
            bool: 성공 여부
        """
        if not self.embedding:
            return False
        
        try:
            # 벡터 저장소가 없으면 생성
            if self.vectorstore is None:
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
            result = self.learn_from_file(tmp_path, metadata)
            
            # 임시 파일 삭제
            os.unlink(tmp_path)
            
            return result
        
        except Exception as e:
            print(f"텍스트 학습 중 오류 발생: {e}")
            return False
    
    def search_similar_documents(self, query: str, top_k: int = 5) -> List[Document]:
        """
        쿼리와 유사한 문서 검색
        
        Args:
            query (str): 검색 쿼리
            top_k (int): 반환할 문서 수
            
        Returns:
            List[Document]: 검색된 문서 목록
        """
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
        if not self.vectorstore or not self.api_key:
            return {}
        
        try:
            # 유사 문서 검색
            documents = self.search_similar_documents(query)
            
            if not documents:
                return {}
            
            # 검색된 문서 내용 조합
            context = "\n\n".join([doc.page_content for doc in documents])
            
            # OpenAI API를 사용하여 템플릿 데이터 생성
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 소프트웨어 구현 명세서 작성을 도와주는 전문가입니다. 제공된 문서와 사용자 입력을 분석하여 소프트웨어 구현 명세서의 각 섹션별 내용을 JSON 형식으로 구성해주세요."},
                    {"role": "user", "content": f"다음은 참조할 문서 내용입니다:\n\n{context}\n\n사용자 입력: {query}"}
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