from app.db.database import db
from typing import Dict, Any, List

class EnrichmentService:
    
    # --- PHẦN 1: XỬ LÝ LOGIC TEMPLATE (MỚI THÊM) ---
    
    def _format_structure_template(self, mongo_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Biến đổi dữ liệu thô -> Template A (Cấu trúc)
        """
        parts = []
        texts = mongo_doc.get("text", {})
        blobs = mongo_doc.get("blobs", {})
        
        # Mapping để tìm bbox chuẩn xác nhất (Ưu tiên bbox của Blob bao quanh Text)
        # 1. Tạo dict mapping: ID Text -> ID Blob chứa nó (dựa vào quan hệ intraObject)
        text_to_blob = {}
        relationships = mongo_doc.get("relationships", {})
        for rel in relationships.values():
            if rel.get("category") == "intraObject":
                text_to_blob[rel["target"]] = rel["origin"]

        # 2. Duyệt qua các text để tạo danh sách parts
        for t_id, t_data in texts.items():
            name = t_data.get("value") or t_data.get("utf8_value") or "Unknown"
            
            # Tìm bbox: Lấy của Blob nếu có, không thì lấy của Text
            bbox = t_data.get("bbox") 
            if t_id in text_to_blob:
                blob_id = text_to_blob[t_id]
                if blob_id in blobs:
                    bbox = blobs[blob_id].get("bbox")

            parts.append({
                "entity_id": t_id,
                "name": name,
                "description": f"Một phần của {mongo_doc.get('category', 'hệ thống')}", # Có thể customize sau
                "bbox": bbox
            })
            
        return {
            "summary": f"Biểu đồ mô tả cấu tạo gồm {len(parts)} thành phần.",
            "parts": parts
        }

    def _format_cycle_template(self, mongo_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Biến đổi dữ liệu thô -> Template B (Chu trình)
        Dựa vào mũi tên (arrows) trong 'interObject' relationships
        """
        stages = []
        texts = mongo_doc.get("text", {})
        
        # 1. Tạo map ID -> Name để dễ tra cứu
        id_to_name = {k: v.get("value", "") for k, v in texts.items()}
        
        # 2. Phân tích các mũi tên để tìm quan hệ "Next Step"
        # connections = { "T1": "T2", "T2": "T3" ... }
        connections = {} 
        relationships = mongo_doc.get("relationships", {})
        
        for rel in relationships.values():
            if rel.get("category") == "interObject":
                origin = rel.get("origin")
                target = rel.get("target")
                
                # Cần map ngược từ Blob ID về Text ID (nếu mũi tên nối Blob)
                # (Logic này hơi phức tạp, tạm thời giả định mũi tên nối thẳng Text hoặc Blob đã map name)
                # Để đơn giản cho demo: Ta chỉ lấy tên
                origin_name = id_to_name.get(origin, origin) # Nếu ko có tên thì lấy ID
                target_name = id_to_name.get(target, target)
                
                if origin_name and target_name:
                    connections[origin_name] = target_name

        # 3. Tạo danh sách Stages
        step_count = 1
        for t_id, t_data in texts.items():
            name = t_data.get("value")
            if not name: continue
            
            next_step_name = connections.get(name) # Tìm xem thằng này trỏ đi đâu
            
            stages.append({
                "step": step_count,
                "name": name,
                "description": f"Giai đoạn {name}",
                "next_step": next_step_name if next_step_name else "End"
            })
            step_count += 1
            
        # Sắp xếp lại stages nếu cần (hiện tại đang list theo thứ tự tìm thấy)
        return {
            "summary": "Vòng đời/Quy trình diễn ra theo các bước sau.",
            "stages": stages
        }

    # --- PHẦN 2: LOGIC CHÍNH (GIỮ NGUYÊN & GỌI HÀM TRÊN) ---

    def get_related_diagrams(self, current_diagram_id: str):
        if db.pg_conn is None or db.pg_conn.closed:
            db.connect()
        cursor = db.pg_conn.cursor()

        # Lấy từ khóa
        sql_get_entities = "SELECT DISTINCT content FROM entities WHERE diagram_id = %s AND type = 'text'"
        cursor.execute(sql_get_entities, (current_diagram_id,))
        keywords = [row['content'] for row in cursor.fetchall()]

        if not keywords:
            return [], []

        # Tìm liên kết
        sql_find_relations = """
            SELECT DISTINCT e.diagram_id, d.category, e.content as matched_keyword
            FROM entities e JOIN diagrams d ON e.diagram_id = d.id
            WHERE e.content = ANY(%s) AND e.diagram_id != %s 
            LIMIT 10;
        """
        cursor.execute(sql_find_relations, (keywords, current_diagram_id))
        raw_results = cursor.fetchall()
        cursor.close()

        # Format kết quả liên kết
        related_knowledge = []
        for row in raw_results:
            related_knowledge.append({
                "concept": row['matched_keyword'],
                "found_in_diagram": row['diagram_id'],
                "category": row['category'],
                "relation": "appears_in",
                "thumbnail_url": f"https://ai2d.r2.cloudflarestorage.com/ai2d/raw/{row['diagram_id']}"
            })

        return keywords, related_knowledge

    def process_template_data(self, template_type: str, mongo_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hàm Router: Quyết định dùng hàm format nào dựa vào template_type
        """
        if not mongo_doc:
            return {}
            
        if template_type == "structure_view":
            return self._format_structure_template(mongo_doc)
        elif template_type == "process_view":
            return self._format_cycle_template(mongo_doc)
        else:
            # Fallback nếu không khớp
            return {"raw": mongo_doc}

# Tạo instance
enrichment_service = EnrichmentService()