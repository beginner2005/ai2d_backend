# Hàm connect Mongo & Postgres
from pymongo import MongoClient
import psycopg2
from neo4j import GraphDatabase
from psycopg2.extras import RealDictCursor
from app.core.config import settings

class Database:
    def __init__(self):
        self.mongo_client = None
        self.mongo_db = None
        self.pg_conn = None
        self.neo4j_driver = None

    def connect(self):
        # 1. Connect MongoDB
        try:
            self.mongo_client = MongoClient(settings.MONGO_URL)
            self.mongo_db = self.mongo_client[settings.MONGO_DB_NAME]
            print("Connected to MongoDB!")
        except Exception as e:
            print(f"Failed to connect MongoDB: {e}")

        # 2. Connect PostgreSQL
        try:
            self.pg_conn = psycopg2.connect(
                host=settings.POSTGRES_SERVER,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                port=settings.POSTGRES_PORT,
                sslmode='require',
                cursor_factory=RealDictCursor # Để kết quả trả về dạng Dict {key: value}
            )
            print("Connected to PostgreSQL!")
        except Exception as e:
            print(f"Failed to connect PostgreSQL: {e}")

        # 3. Connect Neo4j
        try:
            self.neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.neo4j_driver.verify_connectivity()
            print("Connected to Neo4j Aura!")
        except Exception as e:
            print(f"Failed to connect Neo4j: {e}")

    def close(self):
        if self.mongo_client:
            self.mongo_client.close()
        if self.pg_conn:
            self.pg_conn.close()
        if self.neo4j_driver: 
            self.neo4j_driver.close()

# Tạo 1 instance dùng chung
db = Database()