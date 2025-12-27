import os
import sys
from pymongo import MongoClient
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Import module app nếu cần (để chắc chắn path đúng)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

# --- CẤU HÌNH ---
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")

def get_text_mapping(json_doc):
    """
    Hàm này tạo từ điển map ID -> Text Content
    Ví dụ: {'T1': 'Sun', 'B1': 'Sun'} (Nếu B1 chứa T1)
    """
    id_to_text = {}
    
    # 1. Map Text ID -> Nội dung Text
    texts = json_doc.get('text', {})
    for t_id, t_data in texts.items():
        # AI2D gốc lưu text value trong 'value' hoặc 'utf8_value'
        content = t_data.get('value') or t_data.get('utf8_value') or "Unknown"
        id_to_text[t_id] = content

    # 2. Map Blob ID -> Nội dung Text (Dựa vào quan hệ intraObject)
    # Trong AI2D, quan hệ 'intraObject' chỉ ra Text nào gán nhãn cho Blob nào
    relationships = json_doc.get('relationships', {})
    for rel_id, rel_data in relationships.items():
        if rel_data.get('category') == 'intraObject':
            origin = rel_data.get('origin') # Thường là ID của Blob
            target = rel_data.get('target') # Thường là ID của Text
            
            # Nếu target là text đã biết, gán text đó cho blob origin
            if target in id_to_text:
                id_to_text[origin] = id_to_text[target]

    return id_to_text

def sync_data():
    print("⏳ Đang kết nối MongoDB & Neo4j...")
    
    # Kết nối
    mongo_client = MongoClient(MONGO_URL)
    mongo_db = mongo_client[MONGO_DB_NAME]
    collection = mongo_db["diagrams"]
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    
    # Lấy toàn bộ sơ đồ
    cursor = collection.find({})
    total_docs = collection.count_documents({})
    print(f"✅ Tìm thấy {total_docs} sơ đồ trong MongoDB.")

    count = 0
    with driver.session() as session:
        for doc in cursor:
            diagram_id = doc.get('id') or doc.get('_id') # ID ảnh (vd: 4859.png)
            
            # 1. Tạo Node Diagram
            # Lấy category từ Postgres là tốt nhất, nhưng ở đây tạm lấy 'Unknown' hoặc từ JSON nếu có
            session.run("""
                MERGE (d:Diagram {id: $id})
                SET d.storage_path = 'https://ai2d.r2.cloudflarestorage.com/ai2d/raw/' + $id
            """, id=diagram_id)

            # 2. Chuẩn bị Mapping (ID -> Tên concept)
            id_map = get_text_mapping(doc)
            
            # 3. Duyệt các quan hệ (Relationships) để vẽ Graph
            relationships = doc.get('relationships', {})
            has_arrows = False
            
            for rel_id, rel_data in relationships.items():
                category = rel_data.get('category')
                
                # Chỉ quan tâm quan hệ giữa các vật (interObject) -> Mũi tên
                if category == 'interObject':
                    origin_id = rel_data.get('origin')
                    target_id = rel_data.get('target')
                    relation_type = rel_data.get('relation', 'related_to') # vd: arrowHeadTail
                    
                    # Chỉ vẽ nếu cả 2 đầu đều định danh được tên (Text)
                    if origin_id in id_map and target_id in id_map:
                        origin_text = id_map[origin_id]
                        target_text = id_map[target_id]
                        
                        # Bỏ qua nếu nối chính nó hoặc text rỗng
                        if origin_text == target_text or not origin_text:
                            continue

                        has_arrows = True
                        
                        # Cypher query: Tạo 2 Concept và nối mũi tên
                        query = """
                        MATCH (d:Diagram {id: $diagram_id})
                        
                        MERGE (c1:Concept {name: $t1})
                        MERGE (c2:Concept {name: $t2})
                        
                        MERGE (d)-[:CONTAINS]->(c1)
                        MERGE (d)-[:CONTAINS]->(c2)
                        
                        MERGE (c1)-[:CONNECTED_TO {type: $rel_type}]->(c2)
                        """
                        session.run(query, 
                                    diagram_id=diagram_id, 
                                    t1=origin_text, 
                                    t2=target_text,
                                    rel_type=relation_type)

            # Nếu sơ đồ không có mũi tên nào (hoặc không map được), 
            # ít nhất hãy nối Diagram với các Text tìm thấy (Fallback)
            if not has_arrows:
                for text_content in set(id_map.values()):
                    if len(text_content) > 1:
                        session.run("""
                            MATCH (d:Diagram {id: $id})
                            MERGE (c:Concept {name: $text})
                            MERGE (d)-[:CONTAINS]->(c)
                        """, id=diagram_id, text=text_content)

            count += 1
            if count % 100 == 0:
                print(f"   -> Đã xử lý {count}/{total_docs} sơ đồ...")

    print("🎉 HOÀN TẤT! Neo4j đã được nâng cấp với dữ liệu gốc.")
    driver.close()
    mongo_client.close()

if __name__ == "__main__":
    sync_data()