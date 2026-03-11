import os
import json
import chromadb
from ollama import Client  # Ollama를 통해 Llama 3.1 사용

# 1. 초기 설정
COLLECTION_NAME = "seoul_restaurant_final"
DB_PATH = os.path.join(os.getcwd(), "my_vector_db")
ollama_client = Client(host='http://localhost:11434')

# ChromaDB 로컬 클라이언트 연결
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_collection(name=COLLECTION_NAME)

# --- 핵심 로직 함수들 ---

def analyze_intent(user_query):
    print(f"DEBUG: 의도 분석 중... ({user_query})") # 진행 상황 출력 추가
    prompt = f"사용자 질문: '{user_query}'\n맛집 검색 키워드(지역, 음식)만 쉼표로 구분해줘."
    try:
        response = ollama_client.generate(model='llama3.1', prompt=prompt)
        print(f"DEBUG: 분석 완료 -> {response['response']}")
        return response['response'].strip()
    except Exception as e:
        print(f"❌ Ollama 에러: {e}")
        return "강남, 맛집" # 에러 시 기본값 반환

def search_restaurants(intent_data):
    """
    intent_data: Llama가 분석한 JSON 객체 
    예: {"query": "강남구 냉면집", "location": "강남구", "menu": "냉면"}
    """
    
    # 1. 메타데이터 필터 구성 (Llama가 뽑아준 정보 활용)
    search_filter = {}
    if intent_data.get('location'):
        search_filter["address"] = {"$contains": intent_data['location']}
    if intent_data.get('menu'):
        search_filter["menu"] = {"$contains": intent_data['menu']}

    # 2. 필터링된 결과 내에서 벡터 검색 수행
    results = collection.query(
        query_texts=[intent_data['query']],
        where=search_filter,  # 이 부분이 핵심입니다!
        n_results=5
    )
    
    candidates = []
    for i in range(len(results['documents'][0])):
        candidates.append({
            "name": results['metadatas'][0][i]['name'],
            "menu": results['metadatas'][0][i]['menu'],
            "address": results['metadatas'][0][i]['address'],
            "description": results['documents'][0][i]
        })
    return candidates

def rerank_results(user_query, candidates):
    """Llama 3.1을 사용하여 검색된 후보들의 우선순위를 다시 정합니다."""
    candidate_str = json.dumps(candidates, ensure_ascii=False)
    prompt = f"질문: {user_query}\n후보리스트: {candidate_str}\n위 후보 중 질문에 가장 적합한 순서대로 정렬해서 JSON 리스트 형식으로만 출력해줘."
    
    response = ollama_client.generate(model='llama3.1', prompt=prompt)
    # 실제 구현시에는 JSON 파싱 로직이 필요하지만, 여기서는 후보를 그대로 반환하거나 간단히 정제합니다.
    return candidates 

def generate_answer(user_query, ranked_data):
    """최종적으로 사용자에게 보여줄 친절한 답변을 생성합니다."""
    restaurant_names = ", ".join([r['name'] for r in ranked_data])
    prompt = f"질문: {user_query}\n추천 식당: {restaurant_names}\n위 식당들을 기반으로 맛깔나는 추천 답변을 작성해줘."
    
    response = ollama_client.generate(model='llama3.1', prompt=prompt)
    return response['response']

# 테스트용 코드 (직접 실행 시에만 작동)
if __name__ == "__main__":
    test_query = "강남 근처 맛집 추천해줘"
    intent = analyze_intent(test_query)
    results = search_restaurants(intent)
    print(f"검색 결과: {results}")