from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 기존 RAG 로직 임포트
try:
    # 파일명이 query_test2.py가 맞는지, 같은 폴더에 있는지 확인하세요.
    import query_test2
    from query_test2 import analyze_intent, search_restaurants, rerank_results, generate_answer
    print("✅ 모든 로직 함수를 성공적으로 불러왔습니다.")
except ImportError as e:
    print(f"❌ 임포트 에러 상세: {e}")

app = FastAPI(title="Seoul Food AI Backend")

# CORS 설정 (프론트엔드 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"], # OPTIONS는 Preflight 요청 대응에 필수입니다.
    allow_headers=["*"],  # 모든 헤더 허용
)

class QueryRequest(BaseModel):
    question: str

# 1번 엔드포인트: AI 맛집 검색 (Vue에서 호출)
@app.post("/ask")
async def ask_question(request: QueryRequest):
    intent = analyze_intent(request.question)
    candidates = search_restaurants(intent)
    ranked_data = rerank_results(request.question, candidates)
    answer = generate_answer(request.question, ranked_data)
    return {"answer": answer, "metadata": ranked_data}

# 2번 엔드포인트: 서버 상태 확인용 (브라우저 접속용)
@app.get("/")
async def root():
    return {"message": "AI 맛집 검색 서버가 정상 작동 중입니다."}

# 3번 엔드포인트: (예시) 현재 등록된 식당 개수 조회
@app.get("/status")
async def get_status():
    # 여기서 DB count 등을 수행할 수 있습니다.
    return {"status": "online", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)