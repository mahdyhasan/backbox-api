-- ==========================================
-- BLACK BOX CORE ENGINE - COMPLETE SCHEMA
-- Version: 2.0 - Fresh installation
-- ==========================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- 2. DROP EXISTING TABLES (FRESH START)
-- ==========================================
DROP TABLE IF EXISTS usage_logs CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS client_assigned_providers CASCADE;
DROP TABLE IF EXISTS app_allowed_providers CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS apps CASCADE;
DROP TABLE IF EXISTS models CASCADE;
DROP TABLE IF EXISTS providers CASCADE;
DROP TABLE IF EXISTS admin_users CASCADE;

-- ==========================================
-- 3. CORE ENTITIES
-- ==========================================

-- A. LLM PROVIDERS (OpenAI, Anthropic, Groq, etc.)
CREATE TABLE providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    api_key_encrypted TEXT,
    base_url VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'degraded')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- B. MODELS (Specific models belonging to providers)
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID REFERENCES providers(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    identifier VARCHAR(100) NOT NULL,
    context_window INTEGER,
    input_cost_per_1k NUMERIC(10, 6) DEFAULT 0.0,
    output_cost_per_1k NUMERIC(10, 6) DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(provider_id, identifier)
);

-- C. APPLICATIONS (The Products/Solutions: AURA, Sales Analyzer)
CREATE TABLE apps (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    type VARCHAR(50) DEFAULT 'SaaS',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    settings JSONB DEFAULT '{"default_chunk_size": 400, "retrieval_depth": 8}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- D. APP_ALLOWED_PROVIDERS (Many-to-Many: Apps can use multiple LLMs)
CREATE TABLE app_allowed_providers (
    app_id VARCHAR REFERENCES apps(id) ON DELETE CASCADE,
    provider_id UUID REFERENCES providers(id) ON DELETE CASCADE,
    daily_token_limit INTEGER DEFAULT 100000,
    PRIMARY KEY (app_id, provider_id)
);

-- E. CLIENTS (Paying Customers of Apps)
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id VARCHAR REFERENCES apps(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    external_id VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'Basic',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
    scope_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- F. CLIENT_ASSIGNED_PROVIDERS (Many-to-Many: Clients can have specific LLMs enabled)
CREATE TABLE client_assigned_providers (
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    provider_id UUID REFERENCES providers(id) ON DELETE CASCADE,
    monthly_budget_cap NUMERIC(10, 2),
    PRIMARY KEY (client_id, provider_id)
);

-- ==========================================
-- 4. AUTHENTICATION & SECURITY
-- ==========================================

-- G. API_KEYS (Hierarchy: Platform -> App -> Client)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_prefix VARCHAR(30) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    scope_level VARCHAR(20) NOT NULL CHECK (scope_level IN ('platform', 'app', 'client')),
    app_id VARCHAR REFERENCES apps(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- H. ADMIN_USERS (Super Admins for this Dashboard)
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 5. OPERATIONAL DATA
-- ==========================================

-- I. DOCUMENTS (Metadata for ingested files)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id VARCHAR REFERENCES apps(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    file_name VARCHAR(255),
    file_type VARCHAR(50),
    storage_path VARCHAR(500),
    status VARCHAR(20) DEFAULT 'processing',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- J. USAGE_LOGS (Audit & Billing)
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    app_id VARCHAR REFERENCES apps(id),
    client_id UUID REFERENCES clients(id),
    provider_id UUID REFERENCES providers(id),
    model_id UUID REFERENCES models(id),
    request_type VARCHAR(50),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_cost NUMERIC(10, 6),
    latency_ms INTEGER,
    status_code INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 6. INDEXES FOR PERFORMANCE
-- ==========================================

CREATE INDEX idx_usage_logs_app ON usage_logs(app_id);
CREATE INDEX idx_usage_logs_client ON usage_logs(client_id);
CREATE INDEX idx_usage_logs_date ON usage_logs(created_at);
CREATE INDEX idx_documents_client ON documents(client_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- ==========================================
-- 7. TRIGGERS & FUNCTIONS
-- ==========================================

-- Function to auto-update 'updated_at' timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Apply trigger to providers and apps
CREATE TRIGGER update_provider_modtime
    BEFORE UPDATE ON providers
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_app_modtime
    BEFORE UPDATE ON apps
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Function to generate Scope ID on Client creation
CREATE OR REPLACE FUNCTION generate_client_scope()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.scope_id IS NULL THEN
        NEW.scope_id := CONCAT(SUBSTRING(NEW.app_id, 1, 8), '::', SUBSTRING(NEW.id::text, 1, 8));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER trigger_generate_scope
    BEFORE INSERT ON clients
    FOR EACH ROW EXECUTE FUNCTION generate_client_scope();

-- ==========================================
-- 8. SEED INITIAL DATA
-- ==========================================

-- Seed Anthropic Provider
INSERT INTO providers (name, display_name, base_url, status)
VALUES (
    'anthropic',
    'Anthropic Claude',
    'https://api.anthropic.com',
    'active'
);

-- Seed Groq Provider
INSERT INTO providers (name, display_name, base_url, status)
VALUES (
    'groq',
    'Groq',
    'https://api.groq.com',
    'active'
);

-- Seed Anthropic Claude Sonnet Model
INSERT INTO models (provider_id, name, identifier, context_window, input_cost_per_1k, output_cost_per_1k, is_active)
SELECT id, 'Claude Sonnet 4', 'claude-sonnet-4-20250514', 8192, 0.003, 0.015, TRUE
FROM providers WHERE name = 'anthropic';

-- Seed Groq Llama 3.3 Model
INSERT INTO models (provider_id, name, identifier, context_window, input_cost_per_1k, output_cost_per_1k, is_active)
SELECT id, 'Llama 3.3 70B', 'llama-3.3-70b-versatile', 8192, 0.0001, 0.0001, TRUE
FROM providers WHERE name = 'groq';

-- Seed Apps
INSERT INTO apps (id, name, description, status) VALUES
('aura', 'aura', 'AURA AI Chatbot - Conversational RAG solution', 'active'),
('sales-analyzer', 'sales-analyzer', 'Sales Call Analyzer - Audio transcript analysis', 'active');

-- Seed Demo Client for Aura
INSERT INTO clients (app_id, name, external_id, plan)
VALUES ('aura', 'Acme Corporation', 'acme-ext-001', 'enterprise');

-- Seed Platform Key
INSERT INTO api_keys (key_prefix, key_hash, scope_level)
VALUES ('bb_platform_', crypt('demo_platform_key_hash', 'sha256'), 'platform');

-- Seed App Key for Aura
INSERT INTO api_keys (key_prefix, key_hash, scope_level, app_id)
VALUES ('bb_app_aura_', crypt('demo_app_aura_key_hash', 'sha256'), 'app', 'aura');

-- Seed Client Key for Acme Corp
INSERT INTO api_keys (key_prefix, key_hash, scope_level, app_id, client_id)
SELECT 'bb_client_aura_acme-corp_', crypt('demo_client_key_hash', 'sha256'), 'client', 'aura', id
FROM clients WHERE name = 'Acme Corporation';

-- Seed Admin User
INSERT INTO admin_users (email, password_hash, role)
VALUES ('admin@augmex.com', crypt('demo_password', 'sha256'), 'super_admin');

-- ==========================================
-- SCHEMA COMPLETE
-- ==========================================