# File chạy chính của Server
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
    status = {"status": "ok", "mongo": "dead", "postgres": "dead"}
    
    # Test Mongo: Đếm số lượng diagrams
    try:
        if db.mongo_db is not None:
            count = db.mongo_db["diagrams"].count_documents({})
            status["mongo"] = f"alive ({count} docs)"
    except Exception as e:
        status["mongo"] = str(e)

    # Test Postgres: Đếm số lượng diagrams
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
        status["postgres"] = str(e)

    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
