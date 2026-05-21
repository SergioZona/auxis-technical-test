CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT NOW(),
    document_type VARCHAR,
    doc_date VARCHAR,
    doc_number VARCHAR,
    vendor_name VARCHAR,
    client_name VARCHAR,
    total_amount FLOAT,
    tax_amount FLOAT,
    extraction_method VARCHAR,
    file_size_bytes INTEGER,
    page_count INTEGER,
    processing_time_ms INTEGER,
    tables JSONB NOT NULL DEFAULT '[]'::jsonb,
    extras JSONB NOT NULL DEFAULT '{}'::jsonb
);
