from app.db.database import db

class EnrichmentService:
    def get_related_diagrams(self, current_diagram_id: str):
        """
        Thuật toán:
        1. Lấy tất cả entities của ảnh hiện tại.
        2. Tìm xem các entities đó còn xuất hiện ở ảnh nào khác không.
        3. Gom nhóm lại.
        """
        if db.pg_conn is None or db.pg_conn.closed:
            db.connect()
            
        cursor = db.pg_conn.cursor()

        # 1: Lấy các từ khóa (entities) trong ảnh hiện tại
        # Chỉ lấy Text, bỏ qua mũi tên hay khung hình
        sql_get_entities = """
            SELECT DISTINCT content 
            FROM entities 
            WHERE diagram_id = %s AND type = 'text' AND content IS NOT NULL
        """
        cursor.execute(sql_get_entities, (current_diagram_id,))
        # Tạo danh sách từ khóa, ví dụ: ['Frog', 'Eggs', 'Water']
        keywords = [row['content'] for row in cursor.fetchall()]

        if not keywords:
            return [], [] # Không có text nào để tìm liên kết

        # 2: Tìm các ảnh khác có chứa cùng từ khóa (Thuật toán đảo ngược)
        # Sử dụng ANY(%s) để tìm nhanh trong danh sách
        sql_find_relations = """
            SELECT DISTINCT e.diagram_id, d.category, e.content as matched_keyword
            FROM entities e
            JOIN diagrams d ON e.diagram_id = d.id
            WHERE e.content = ANY(%s) 
            AND e.diagram_id != %s  -- Không lấy chính ảnh đang xem
            LIMIT 10; -- Giới hạn 10 kết quả gợi ý
        """
        
        cursor.execute(sql_find_relations, (keywords, current_diagram_id))
        raw_results = cursor.fetchall()
        cursor.close()

        # 3: Format dữ liệu trả về (Mapping)
        related_knowledge = []
        for row in raw_results:
            related_knowledge.append({
                "concept": row['matched_keyword'],  # Từ khóa chung (VD: Frog)
                "found_in_diagram": row['diagram_id'],
                "category": row['category'],
                "relation": "appears_in", # Quan hệ đơn giản: "Xuất hiện trong"
                "thumbnail_url": f"https://.../ai2d/raw/{row['diagram_id']}" 
            })

        return keywords, related_knowledge

# Tạo instance để dùng
enrichment_service = EnrichmentService()