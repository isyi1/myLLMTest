import sys

# 실행 즉시 화면에 찍히는지 확인
print("!!! 파이썬 실행 시작 !!!")

try:
    import chromadb
    print("ChromaDB 라이브러리 로드 성공")
    
    client = chromadb.HttpClient(host='localhost', port=8000)
    print(f"서버 연결 시도 중... 결과: {client.heartbeat()}")
    
    # 컬렉션 정보 가져오기
    cols = client.list_collections()
    print(f"현재 컬렉션 목록: {cols}")

except Exception as e:
    print(f"에러 발생: {e}")

print("!!! 파이썬 실행 종료 !!!")