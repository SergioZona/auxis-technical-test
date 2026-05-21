CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR NOT NULL,
    upload_date TIMESTAMP NOT NULL DEFAULT NOW(),
    form_type VARCHAR,
    tax_year INTEGER,
    nit_employer VARCHAR,
    employer_name VARCHAR,
    employee_document_id VARCHAR,
    employee_name VARCHAR,
    period_start VARCHAR,
    period_end VARCHAR,
    total_gross_income FLOAT,
    income_tax_withheld FLOAT,
    extraction_method VARCHAR,
    file_size_bytes INTEGER,
    page_count INTEGER,
    processing_time_ms INTEGER,
    extras JSONB NOT NULL DEFAULT '{}'::jsonb
);
