-- PostgreSQL Row Level Security Setup - Inteligente
-- Solo aplica RLS a tablas que tienen tenant_id

-- 1. Crear función para obtener tenant_id actual
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(current_setting('app.current_tenant_id', true)::INTEGER, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- 2. Aplicar RLS solo a tablas que tienen tenant_id
DO $$
DECLARE
    table_name TEXT;
    tables_with_tenant_id TEXT[] := ARRAY[
        'auth_api_user',
        'employees_api_employee', 
        'clients_api_client',
        'pos_api_sale',
        'payroll_api_payrollsettlement',
        'employees_api_earning'
    ];
BEGIN
    FOREACH table_name IN ARRAY tables_with_tenant_id
    LOOP
        -- Verificar si la tabla existe y tiene tenant_id
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = table_name 
            AND column_name = 'tenant_id'
            AND table_schema = 'public'
        ) THEN
            -- Habilitar RLS
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
            
            -- Crear política
            EXECUTE format('
                CREATE POLICY tenant_isolation_%s ON %I
                FOR ALL TO PUBLIC
                USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0)
            ', replace(table_name, '_', ''), table_name);
            
            RAISE NOTICE 'RLS aplicado a tabla: %', table_name;
        ELSE
            RAISE NOTICE 'Tabla % no tiene tenant_id, omitiendo', table_name;
        END IF;
    END LOOP;
END
$$;

-- 3. Política especial para tenants_api_tenant
ALTER TABLE tenants_api_tenant ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_tenants ON tenants_api_tenant
    FOR ALL TO PUBLIC
    USING (id = current_tenant_id() OR current_tenant_id() = 0);