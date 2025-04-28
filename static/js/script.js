document.addEventListener('DOMContentLoaded', () => {
    // 폼 제출 시 유효성 검사
    const documentForm = document.querySelector('.document-form');
    
    if (documentForm) {
        documentForm.addEventListener('submit', (e) => {
            const titleInput = document.getElementById('document_title');
            const contentInput = document.getElementById('document_content');
            
            if (!titleInput.value.trim()) {
                e.preventDefault();
                alert('문서 제목을 입력해주세요.');
                titleInput.focus();
                return;
            }
            
            if (!contentInput.value.trim()) {
                e.preventDefault();
                alert('문서 내용을 입력해주세요.');
                contentInput.focus();
                return;
            }
            
            // 폼 제출 시 로딩 표시
            const submitButton = document.querySelector('.btn-create');
            submitButton.textContent = '문서 생성 중...';
            submitButton.disabled = true;
        });
    }
    
    // 텍스트 영역 자동 크기 조절
    const textarea = document.getElementById('document_content');
    if (textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }
    
    // 로그인 상태에 따른 버튼 표시
    const checkLoginStatus = () => {
        fetch('/api/login-status')
            .then(response => response.json())
            .then(data => {
                const loginBtn = document.querySelector('.btn-login');
                const logoutBtn = document.querySelector('.btn-logout');
                
                if (data.loggedIn) {
                    loginBtn.style.display = 'none';
                    logoutBtn.style.display = 'block';
                } else {
                    loginBtn.style.display = 'block';
                    logoutBtn.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('로그인 상태 확인 중 오류 발생:', error);
            });
    };
    
    // 로그인 상태 확인 API 추가 필요
    // checkLoginStatus();
}); 