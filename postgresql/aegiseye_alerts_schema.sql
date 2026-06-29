-- AegisEye AI - Alerts Database Schema
CREATE TABLE IF NOT EXISTS public.alertas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES public.cameras(id) ON DELETE SET NULL,
    camera_name VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL, -- critical, warning, medium
    title VARCHAR(255) NOT NULL,
    details TEXT,
    confidence FLOAT,
    trigger_type VARCHAR(100), -- CONCEALMENT_ROI, LINGER_ROI
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast query by tenant
CREATE INDEX IF NOT EXISTS idx_alertas_tenant ON public.alertas(tenant_id);
