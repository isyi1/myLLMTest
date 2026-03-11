import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

embed_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
es = Elasticsearch("http://localhost:9200")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class SearchRequest(BaseModel):
    q: str
    isStream: bool = False  # 기본값은 일반 응답(False)으로 설정

@app.post("/search")
async def search_ai(request: SearchRequest):
    query = request.q
    is_stream_mode = request.isStream

    try:
        # [Step 1] ES 검색 로직 (공통)
        query_vector = embed_model.encode(query).tolist()
        search_body = {
            "knn": { "field": "embedding", "query_vector": query_vector, "k": 5, "num_candidates": 50 },
            "query": { "multi_match": { "query": query, "fields": ["post_sj^3", "fd_reprsnt_menu^2", "subway_info"] } },
            "size": 5
        }
        res = es.search(index="seoul_food", body=search_body)
        hits = res['hits']['hits']
        
        context_parts = []
        metadata = []
        for hit in hits:
            s = hit['_source']
            info = (f"식당명: {s.get('post_sj')}\n"
                    f"메뉴: {s.get('fd_reprsnt_menu')}\n"
                    f"주소: {s.get('new_address')}\n"
                    f"URL: {s.get('post_url')}\n"
                    f"지하철: {s.get('subway_info')}")
            context_parts.append(info)
            metadata.append({"name": s.get('post_sj'), "menu": s.get('fd_reprsnt_menu')})

        context_text = "\n\n---\n\n".join(context_parts)
        prompt = f"""
            당신은 친절하고 전문적인 '서울 맛집 탐방 AI 비서'입니다. 
            제공된 [식당 데이터]를 바탕으로 사용자의 질문에 맞는 최고의 맛집을 추천하세요.

            [응답 규칙]
            1. 인사는 "안녕하세요! 서울 맛집 탐방 AI 비서입니다. 요청하신 맛집 정보를 찾아보았습니다."로 시작하세요.
            2. 각 식당은 아래 마크다운 형식을 반드시 지켜주세요:
               ### 🍴 식당이름 (post_sj)
               - **📍 주소**: {s.get('new_address')}
               - **🔗 바로가기**: [상세정보 보기]({s.get('post_url')})
               - **🚃 오시는 길**: {s.get('subway_info')}
               - **💡 추천 이유**: (데이터의 메뉴 정보를 바탕으로 한 문장 작성)
            3. 식당 사이에는 '---' 구분선을 넣으세요.
            4. 데이터에 없는 식당은 절대 지어내지 마세요.

        [식당 데이터]
        {context_text}

        [질문]
        {query}
        """

        # [Step 2] 모드에 따른 분기 처리
        if is_stream_mode:
            # --- 스트리밍 응답 (SSE) ---
            async def groq_generator():
                meta_payload = json.dumps(metadata)
                yield f"data: __METADATA__{meta_payload}__END__\n\n"

                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        safe_content = content.replace("\n", "[BR]")
                        yield f"data: {safe_content}\n\n"

            return StreamingResponse(groq_generator(), media_type="text/event-stream")
        
        else:
            # --- 일반 응답 (JSON) ---
            chat_completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            answer = chat_completion.choices[0].message.content
            
            return {
                "status": "success",
                "metadata": metadata,
                "answer": answer
            }

    except Exception as e:
        print(f"Error: {e}")
        if is_stream_mode:
            async def error_handler():
                yield f"data: 에러가 발생했습니다: {str(e)}\n\n"
            return StreamingResponse(error_handler(), media_type="text/event-stream")
        else:
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)