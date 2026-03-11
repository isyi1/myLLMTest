import chromadb

# chromaDB Collection 전체 삭제

# ChromaDB 서버 연결
client = chromadb.HttpClient(host='localhost', port=8000)

# 현재 있는 모든 컬렉션 가져오기
collections = client.list_collections()

if not collections:
    print("❌ 삭제할 컬렉션이 없습니다.")
else:
    print(f"🧹 총 {len(collections)}개의 컬렉션을 삭제합니다...")
    for col in collections:
        client.delete_collection(name=col.name)
        print(f"✅ 삭제 완료: {col.name}")
    print("\n✨ 모든 데이터가 초기화되었습니다. 이제 깨끗한 상태입니다!")

# 삭제 확인
print("현재 컬렉션 목록:", client.list_collections())