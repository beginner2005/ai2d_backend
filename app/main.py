from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.database import db
from app.api.v1.endpoints import router as api_router

# Hàm chạy khi server bắt đầu khởi động
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Kết nối DB
    db.connect()
    yield
    # Shutdown: Ngắt kết nối
    db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to AI2D Knowledge Graph API"}

# API KIỂM TRA SỨC KHỎE HỆ THỐNG
@app.get("/health")
def health_check():
    # Mặc định khai báo cả 3 là dead
    status = {"status": "ok", "mongo": "dead", "postgres": "dead", "neo4j": "dead"}
    
    # 1. Test Mongo: Đếm số lượng diagrams
    try:
        if db.mongo_db is not None:
            # Lệnh count_documents({}) đếm tất cả docs
            count = db.mongo_db["diagrams"].count_documents({})
            status["mongo"] = f"alive ({count} docs)"
    except Exception as e:
        status["mongo"] = f"Error: {str(e)}"

    # 2. Test Postgres: Đếm số lượng dòng trong bảng diagrams
    try:
        if db.pg_conn is not None:
            # Check nếu connection bị đóng thì connect lại
            if db.pg_conn.closed:
                db.connect()
                
            cursor = db.pg_conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM diagrams;")
            pg_count = cursor.fetchone()['count']
            status["postgres"] = f"alive ({pg_count} rows)"
            cursor.close()
    except Exception as e:
        status["postgres"] = f"Error: {str(e)}"

    # 3. Test Neo4j: Đếm số lượng Node (Nút)
    try:
        if db.neo4j_driver is not None:
            # Kiểm tra kết nối bằng cách đếm tổng số node
            # MATCH (n) RETURN count(n) là lệnh nhẹ nhất để test
            with db.neo4j_driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) AS count")
                # Lấy kết quả đầu tiên
                neo4j_count = result.single()["count"]
                status["neo4j"] = f"alive ({neo4j_count} nodes)"
    except Exception as e:
        status["neo4j"] = f"Error: {str(e)}"

    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)