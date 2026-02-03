# Database Connector Plugin

SQL and NoSQL database integration for BAEL.

## Features

- ✅ **Multiple Databases:** PostgreSQL, MySQL, MongoDB, Redis
- ✅ **Connection Pooling:** Configurable pool size
- ✅ **Query Execution:** SQL and document queries
- ✅ **Health Checks:** Database connectivity monitoring
- ✅ **Async Support:** Full async/await support

## Installation

```bash
# Install dependencies
pip install sqlalchemy pymongo redis

# Activate plugin
bael plugin load database-connector
```

## Configuration

```yaml
# PostgreSQL
database_type: postgresql
connection_string: "postgresql://user:password@localhost:5432/mydb"
max_connections: 20
timeout: 30

# MongoDB
database_type: mongodb
connection_string: "mongodb://localhost:27017/mydb"

# Redis
database_type: redis
connection_string: "redis://localhost:6379/0"
```

## Usage

```python
# From BAEL
connector = await bael.plugins.get("database-connector")

# Execute SQL query
results = await connector.execute_query(
    "SELECT * FROM users WHERE id = :user_id",
    parameters={"user_id": 123}
)

# MongoDB: Insert document
doc_id = await connector.insert_document(
    "users",
    {"name": "Alice", "email": "alice@example.com"}
)

# MongoDB: Find documents
docs = await connector.find_documents(
    "users",
    {"name": "Alice"}
)

# Get table information
info = await connector.get_table_info("users")

# Get all collections
collections = await connector.get_collections()
```

## Supported Operations

### SQL Databases (PostgreSQL, MySQL)

- `execute_query()` - Execute SQL queries
- `get_table_info()` - Get table schema
- `insert_document()` - Insert records
- `find_documents()` - Query records

### NoSQL Databases (MongoDB)

- `insert_document()` - Insert documents
- `find_documents()` - Query documents
- `get_collections()` - List collections

### Key-Value (Redis)

- Cache operations
- Session storage
- Real-time data

## Examples

### Query Examples

```python
# Find user by ID
users = await connector.execute_query(
    "SELECT id, name, email FROM users WHERE id = :id",
    {"id": 123}
)

# Find all active users
active = await connector.execute_query(
    "SELECT * FROM users WHERE status = :status",
    {"status": "active"}
)

# Count records
count = await connector.execute_query(
    "SELECT COUNT(*) as total FROM users"
)
```

### Document Examples

```python
# Insert user document
user_doc = {
    "name": "Bob",
    "email": "bob@example.com",
    "created_at": datetime.utcnow()
}
doc_id = await connector.insert_document("users", user_doc)

# Find users by query
users = await connector.find_documents(
    "users",
    {"status": "active"}
)
```

## Performance

- **Connection Pool:** Pre-allocated for low-latency access
- **Query Timeout:** Configurable timeout per query
- **Health Checks:** Automatic connection monitoring
- **Async I/O:** Non-blocking database operations

## Permissions

This plugin requires:

- Network access to database server
- Filesystem access for data files (optional)

## License

MIT
