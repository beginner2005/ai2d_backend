from pydantic import BaseModel
from typing import List, Optional, Any, Dict

# --- PHẦN HEALTH CHECK ---
class HealthResponse(BaseModel):
    status: str

# --- PHẦN SEARCH & KNOWLEDGE ---

# 1. Khuôn mẫu cho một kết quả tìm kiếm rút gọn
class SearchResultItem(BaseModel):
    diagram_id: str
    category: str
    storage_path: Optional[str] = None # Link ảnh R2

# 2. Khuôn mẫu cho chi tiết một vật thể (Entity)
class EntityItem(BaseModel):
    entity_id: str
    name: str
    type: str
    bbox: List[int] # [x, y, w, h]

# 3. Khuôn mẫu cho phản hồi chi tiết (API /enrich)
class KnowledgeResponse(BaseModel):
    diagram_id: str
    title: str
    group_type: str
    template_type: str
    
    # Data chính (Sẽ linh động tùy loại biểu đồ)
    data: Dict[str, Any] 
    
    # Phần tri thức làm giàu (Quan trọng)
    related_knowledge: List[Dict[str, Any]] = []