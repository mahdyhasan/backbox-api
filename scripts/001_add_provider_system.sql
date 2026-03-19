-- ==========================================
-- BLACK BOX CORE ENGINE - PROVIDER SYSTEM MIGRATION
-- Version: 2.0
-- ==========================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================
-- 2. CORE ENTITIES
-- ==========================================

-- A. LLM PROVIDERS (OpenAI, Anthropic, Groq, etc.)
CREATE TABLE IF NOT EXISTS providers (
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
CREATE TABLE IF NOT EXISTS models (
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

-- C. APP_ALLOWED_PROVIDERS (Many-to-Many: Apps can use multiple LLMs)
CREATE TABLE IF NOT EXISTS app_allowed_providers (
    app_id VARCHAR REFERENCES apps(id) ON DELETE CASCADE,
    provider_id UUID REFERENCES providers(id) ON DELETE CASCADE,
    daily_token_limit INTEGER DEFAULT 100000,
    PRIMARY KEY (app_id, provider_id)
);

-- ==========================================
-- 3. AUTHENTICATION & SECURITY
-- ==========================================

-- G. API_KEYS (Hierarchy: Platform -> App -> Client)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_prefix VARCHAR(20) NOT NULL,
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
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'admin',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 4. OPERATIONAL DATA
-- ==========================================

-- J. USAGE_LOGS (Audit & Billing)
CREATE TABLE IF NOT EXISTS usage_logs (
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
-- 5. INDEXES FOR PERFORMANCE
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_usage_logs_app ON usage_logs(app_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_client ON usage_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_date ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_client ON documents(client_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);

-- ==========================================
-- 6. MIGRATE EXISTING DATA
-- ==========================================

-- Update apps table structure if needed
DO $$
BEGIN
    -- Add settings column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'apps' AND column_name = 'settings'
    ) THEN
        ALTER TABLE apps ADD COLUMN IF NOT EXISTS settings JSONB DEFAULT '{"default_chunk_size": 400, "retrieval_depth": 8}';
    END IF;
    
    -- Add updated_at column if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'apps' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE apps ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Update clients table structure
DO $$
BEGIN
    -- Add external_id column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'clients' AND column_name = 'external_id'
    ) THEN
        ALTER TABLE clients ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);
    END IF;
    
    -- Add plan column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'clients' AND column_name = 'plan'
    ) THEN
        ALTER TABLE clients ADD COLUMN IF NOT EXISTS plan VARCHAR(50) DEFAULT 'Basic';
    END IF;
    
    -- Add scope_id column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'clients' AND column_name = 'scope_id'
    ) THEN
        ALTER TABLE clients ADD COLUMN IF NOT EXISTS scope_id VARCHAR(255);
    END IF;
    
    -- Generate scope_id for existing clients
    UPDATE clients 
    SET scope_id = CONCAT(SUBSTRING(app_id, 1, 8), '::', SUBSTRING(id::text, 1, 8))
    WHERE scope_id IS NULL;
END $$;

-- Update documents table structure
DO $$
BEGIN
    -- Add storage_path column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'storage_path'
    ) THEN
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS storage_path VARCHAR(500);
    END IF;
    
    -- Add file_type column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'file_type'
    ) THEN
        ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_type VARCHAR(50);
    END IF;
END $$;

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
DROP TRIGGER IF EXISTS update_provider_modtime ON providers;
CREATE TRIGGER update_provider_modtime
    BEFORE UPDATE ON providers
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

DROP TRIGGER IF EXISTS update_app_modtime ON apps;
CREATE TRIGGER update_app_modtime
    BEFORE UPDATE ON apps
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

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
)
ON CONFLICT (name) DO NOTHING;

-- Seed Groq Provider
INSERT INTO providers (name, display_name, base_url, status)
VALUES (
    'groq',
    'Groq',
    'https://api.groq.com',
    'active'
)
ON CONFLICT (name) DO NOTHING;

-- Seed default platform admin user
INSERT INTO admin_users (email, password_hash, role)
VALUES (
    'admin@augmex.com',
    '$2b$12$SomeRandomHashedPasswordHere', -- CHANGE THIS IN PRODUCTION
    'super_admin'
)
ON CONFLICT (email) DO NOTHING;

-- ==========================================
-- MIGRATION COMPLETE
-- ==========================================