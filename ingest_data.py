import json
from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer

# 모델 로드 (생성 시점에 배치 처리가 가능하도록 설정)
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

es = client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def create_index():
    index_name = "seoul_food"
    
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        print(f"기존 '{index_name}' 인덱스를 삭제했습니다.")

    # 핵심: settings(분석기 정의)와 mappings(필드 정의)를 하나의 body에 넣어야 함
    index_body = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "nori_analyzer": {  # 여기서 이름을 정의하고
                        "type": "custom",
                        "tokenizer": "nori_tokenizer"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "pk_id": {"type": "integer"},
                "post_sn": {"type": "long"},
                "post_sj": {"type": "text", "analyzer": "nori_analyzer"}, # 여기서 불러다 씀
                "fd_reprsnt_menu": {"type": "text", "analyzer": "nori_analyzer"},
                "address": {"type": "text", "analyzer": "nori_analyzer"},
                "new_address": {"type": "keyword"},
                "cmmn_telno": {"type": "keyword"},
                "subway_info": {"type": "text", "analyzer": "nori_analyzer"},
                "cmmn_use_time": {"type": "text"},
                "post_url": {"type": "keyword"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    # body 인자로 settings와 mappings를 한꺼번에 전달
    es.indices.create(index=index_name, body=index_body)
    print("✅ 인덱스 및 Nori 분석기 설정 완료!")

def process_and_ingest(batch_size=64): # 배치 사이즈를 설정하여 속도 향상
    with open('seoul_food_store_list.json', 'r', encoding='utf-8') as f:
        data_list = json.load(f).get('DATA', [])

    total = len(data_list)
    print(f"🚀 총 {total}건 처리 시작 (배치 사이즈: {batch_size})")

    # 1. 임베딩할 텍스트 리스트 먼저 생성
    combined_texts = []
    for item in data_list:
        menu = (item.get("fd_reprsnt_menu") or "").strip()
        addr = (item.get("new_address") or "").strip()
        subway = (item.get("subway_info") or "").strip()
        combined_texts.append(f"{addr} {menu} {subway}")

    # 2. 모델 리스트를 통째로 임베딩 (이 부분이 속도의 핵심!)
    # show_progress_bar를 켜면 진행 상황을 볼 수 있습니다.
    print("🧠 임베딩 계산 중...")
    all_embeddings = model.encode(combined_texts, batch_size=batch_size, show_progress_bar=True)

    # 3. ES 액션 리스트 생성
    actions = []
    for idx, (item, vector) in enumerate(zip(data_list, all_embeddings), 1):
        action = {
            "_index": "seoul_food",
            "_id": idx,
            "_source": {
                "pk_id": idx,
                "post_sn": item.get("post_sn"),
                "post_sj": (item.get("post_sj") or "").strip(),
                "fd_reprsnt_menu": (item.get("fd_reprsnt_menu") or "").strip(),
                "new_address": (item.get("new_address") or "").strip(),
                "subway_info": (item.get("subway_info") or "").strip(),
                "embedding": vector.tolist()
            }
        }
        actions.append(action)

        # 4. 벌크 삽입 (메모리 방지를 위해 500개 단위로 실행)
        if len(actions) >= 500:
            helpers.bulk(es, actions)
            actions = []

    if actions:
        helpers.bulk(es, actions)
    
    print(f"✅ 수집 완료!")

if __name__ == "__main__":
    create_index()
    process_and_ingest()