import chromadb

client = chromadb.HttpClient(host='localhost', port=8000)

print("컬렉션 목록:", client.list_collections())
