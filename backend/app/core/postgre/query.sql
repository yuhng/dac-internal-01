select id, row->>'schema_version' as schema_version, created_at
from documents
