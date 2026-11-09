# Smart Warehouse · ERD MVP

```mermaid
erDiagram
    USER ||--o{ STOCK_DOCUMENT : creates
    USER o|--o{ STOCK_DOCUMENT : confirms
    USER o|--o{ AUDIT_LOG : performs
    CATEGORY ||--o{ PRODUCT : groups
    SUPPLIER o|--o{ STOCK_DOCUMENT : supplies
    WAREHOUSE ||--o{ STOCK_DOCUMENT : contains
    STOCK_DOCUMENT ||--|{ STOCK_DOCUMENT_ITEM : includes
    PRODUCT ||--o{ STOCK_DOCUMENT_ITEM : references
    STOCK_DOCUMENT ||--o{ STOCK_MOVEMENT : posts
    PRODUCT ||--o{ STOCK_MOVEMENT : traces
    WAREHOUSE ||--o{ STOCK_MOVEMENT : records
    PRODUCT ||--o{ STOCK_BALANCE : balances
    WAREHOUSE ||--o{ STOCK_BALANCE : stores
    USER {
        bigint id PK
        string username UK
        string password_hash
        enum role "ADMIN MANAGER STAFF VIEWER"
        boolean is_active
    }
    CATEGORY {
        bigint id PK
        string code UK
        string name
        boolean is_active
    }
    PRODUCT {
        bigint id PK
        string sku UK
        bigint category_id FK
        string name
        string unit
        decimal min_stock "18,3 nonnegative"
        decimal default_cost "18,2 nonnegative"
        boolean is_active
    }
    WAREHOUSE {
        bigint id PK
        string code UK
        string name
        string address
        string contact
        boolean is_active
    }
    SUPPLIER {
        bigint id PK
        string code UK
        string name
        string phone
        string email
        string address
        boolean is_active
    }
    STOCK_DOCUMENT {
        bigint id PK
        string document_no UK
        enum type "IN OUT"
        enum status "DRAFT CONFIRMED CANCELLED"
        bigint warehouse_id FK
        bigint supplier_id FK
        bigint created_by_id FK
        bigint confirmed_by_id FK
        datetime created_at
        datetime confirmed_at
        string notes
    }
    STOCK_DOCUMENT_ITEM {
        bigint id PK
        bigint document_id FK
        bigint product_id FK
        decimal quantity "18,3 positive"
        decimal unit_cost "18,2 nonnegative"
    }
    STOCK_MOVEMENT {
        bigint id PK
        bigint document_id FK
        bigint product_id FK
        bigint warehouse_id FK
        decimal signed_qty "18,3 nonzero"
        decimal unit_cost "18,2 nonnegative"
        datetime created_at
    }
    STOCK_BALANCE {
        bigint id PK
        bigint warehouse_id FK
        bigint product_id FK
        decimal quantity_on_hand "18,3 nonnegative"
        datetime updated_at
    }
    AUDIT_LOG {
        bigint id PK
        bigint actor_id FK
        string action
        string model_name
        string object_id
        json changes
        datetime created_at
    }
```

- Unique theo cặp: balance `(warehouse, product)`, dòng phiếu `(document, product)`, movement `(document, product)`.
- Mã danh mục, SKU, kho và nhà cung cấp có unique không phân biệt chữ hoa/thường.
- Quan hệ dữ liệu nghiệp vụ dùng `PROTECT`; lưu trữ danh mục bằng `is_active`, không xóa lịch sử.
- Phiếu chỉ thay đổi tồn khi Manager/Admin xác nhận. Một transaction khóa phiếu → kho → sản phẩm theo ID → số dư; khóa kho bảo vệ cả số dư chưa tồn tại.
- `StockMovement` và `AuditLog` chỉ thêm; chỉnh sửa bằng các luồng nghiệp vụ mới. UI/API không cung cấp thao tác ghi đè lịch sử.
- Mỗi SKU có một đơn vị cố định sau giao dịch đầu tiên. Giá trị tồn là ước tính theo `default_cost`, không phải FIFO hoặc định giá kế toán.
- Chuyển kho, kiểm kê, lô, barcode thuộc P2, chưa nằm trong schema MVP.
