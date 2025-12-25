from fastapi import APIRouter, HTTPException, Query
from app.db.database import db
from app.schemas.schemas import SearchResultItem, KnowledgeResponse, HealthResponse
from app.services.enrichment import enrichment_service
from app.utils.storage import storage_client
from fastapi.responses import RedirectResponse
from typing import List

router = APIRouter()

# Health Check
@router.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}

# API 1: TÌM KIẾM (Search)
@router.get("/search", response_model=List[SearchResultItem])
async def search_diagrams(
    q: str = Query(..., min_length=2, description="Từ khóa tìm kiếm (VD: frog, cycle)")
):
    if db.pg_conn is None or db.pg_conn.closed:
        db.connect()
    cursor = db.pg_conn.cursor()
    
    # Join với bảng entities để tìm cả chữ bên trong ảnh
    sql = """
        SELECT DISTINCT d.id, d.category, d.storage_path 
        FROM diagrams d
        LEFT JOIN entities e ON d.id = e.diagram_id
        WHERE 
            d.id ILIKE %s 
            OR d.category ILIKE %s 
            OR e.content ILIKE %s 
        LIMIT 20;
    """
    search_term = f"%{q}%"
    cursor.execute(sql, (search_term, search_term, search_term))
    # ---------------------------
    
    results = cursor.fetchall()
    cursor.close()
    
    data = []
    for row in results:
        # Tự động tạo link ảnh cho mỗi kết quả tìm được
        image_link = storage_client.generate_presigned_url(row['id'])
        data.append(SearchResultItem(
            diagram_id=row['id'],
            category=row['category'],
            storage_path=image_link
        ))
    return data

# API 2: LẤY CHI TIẾT (Detail)
@router.get("/diagrams/{diagram_id}")
async def get_diagram_detail(diagram_id: str):
    """
    Lấy metadata chi tiết từ MongoDB
    """
    # 1. Tìm trong Mongo
    doc = db.mongo_db["diagrams"].find_one({"_id": diagram_id})
    
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh này")

    # 2. Chuẩn hóa dữ liệu trả về 
    return {
        "diagram_id": diagram_id,
        "raw_data": doc, # Trả về nguyên cục JSON trong Mongo
        "message": "Dữ liệu thô từ MongoDB"
    }

# API 3: LÀM GIÀU TRI THỨC
@router.get("/enrich/{diagram_id}", response_model=KnowledgeResponse)
async def enrich_knowledge(diagram_id: str):
    """
    Trả về dữ liệu đã được làm giàu + Gợi ý liên kết
    """
    # 1. Lấy thông tin cơ bản từ Postgres
    if db.pg_conn is None or db.pg_conn.closed:
        db.connect()
    cursor = db.pg_conn.cursor()
    
    cursor.execute("SELECT id, category, group_type FROM diagrams WHERE id = %s", (diagram_id,))
    basic_info = cursor.fetchone()
    
    if not basic_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")

    # 2. Lấy chi tiết từ MongoDB (Tọa độ, Bbox...)
    mongo_doc = db.mongo_db["diagrams"].find_one({"_id": diagram_id})
    if not mongo_doc:
        mongo_data = {}
    else:
        # Lọc bớt dữ liệu rác nếu cần, hoặc trả về hết
        mongo_data = {
            "entities": mongo_doc.get("entities", [])
        }

    # 3. CHẠY THUẬT TOÁN LÀM GIÀU (Service Layer)
    keywords, related_list = enrichment_service.get_related_diagrams(diagram_id)

    # 4. Ghép tất cả vào khuôn mẫu JSON (Template)
    response = KnowledgeResponse(
        diagram_id=diagram_id,
        title=f"Biểu đồ về {basic_info['category']}", # Tạm thời tự sinh tiêu đề
        group_type=basic_info['group_type'] or "Unknown",
        template_type="structure_view" if basic_info['group_type'] == 'Structure' else "process_view",
        
        # Dữ liệu chính để vẽ
        data={
            "summary": f"Biểu đồ này chứa các khái niệm: {', '.join(keywords[:5])}...",
            "details": mongo_data
        },
        
        # Dữ liệu liên kết (Knowledge Graph)
        related_knowledge=related_list
    )
    
    return response

# API 4: LẤY ẢNH (UTILS)
@router.get("/diagrams/{diagram_id}/image")
async def get_diagram_image(diagram_id: str):
    """
    Task 4: Trả về link ảnh trực tiếp từ R2 (Redirect luôn sang ảnh cho tiện)
    """
    # 1. Tạo link presigned
    url = storage_client.generate_presigned_url(diagram_id)
    
    if not url:
        raise HTTPException(status_code=404, detail="Không thể tạo link ảnh")
        
    # 2. Redirect người dùng sang link đó luôn
    return RedirectResponse(url)