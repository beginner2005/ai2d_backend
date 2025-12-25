# 1. Chọn hệ điều hành nền tảng
FROM python:3.11-slim

# 2. Tạo thư mục làm việc
WORKDIR /app

# 3. Copy file thư viện vào trước
COPY requirements.txt .

# 4. Cài đặt thư viện (Thêm --no-cache-dir cho nhẹ)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ code vào
COPY . .

# 6. Mở cổng 8000
EXPOSE 8000

# 7. Lệnh chạy server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]