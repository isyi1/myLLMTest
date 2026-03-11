from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 기존에 작성하신 로직 함수들을 가져옵니다.
# 파일명이 query_test2.py라고 가정합니다.
try:
    from query_test2 import analyze_intent, search_restaurants, rerank_results, generate_answer
except ImportError:
    # 파일명이 다르거나 함수가 다른 파일에 있다면 이름을 수정하세요.
    print("⚠️ 'query_test2.py'에서 함수를 불러올 수 없습니다. 파일명을 확인해주세요.")

app = FastAPI()

# 프론트엔드(Vue 3, localhost:5173)와의 통신을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실무에서는 ["http://localhost:5173"] 등 특정 도메인만 허용하는 것이 좋습니다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드 요청 데이터 구조 정의
class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_question(request: QueryRequest):
    """
    프론트엔드로부터 질문을 받아 전체 RAG 프로세스를 실행합니다.
    """
    try:
        user_query = request.question
        
        # 1. Llama 3.1을 이용한 의도 분석
        intent = analyze_intent(user_query)
        
        # 2. ChromaDB 벡터 검색
        candidates = search_restaurants(intent)
        
        # 3. Llama 3.1을 이용한 리랭킹
        ranked_data = rerank_results(user_query, candidates)
        
        # 4. 최종 답변 생성
        answer = generate_answer(user_query, ranked_data)
        
        return {
            "answer": answer,
            "metadata": ranked_data  # 리랭킹된 식당 리스트 정보 전달
        }
        
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 포트 8000번에서 서버 실행
    uvicorn.run(app, host="0.0.0.0", port=8000)