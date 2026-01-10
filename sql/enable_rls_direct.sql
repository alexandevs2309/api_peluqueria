-- PostgreSQL Row Level Security Setup - Directo
-- Solo tablas confirmadas con tenant_id

-- 1. Crear función para obtener tenant_id actual
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(current_setting('app.current_tenant_id', true)::INTEGER, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- 2. Aplicar RLS a tablas confirmadas
-- auth_api_user
ALTER TABLE auth_api_user ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_users ON auth_api_user
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

-- employees_api_employee
ALTER TABLE employees_api_employee ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_employees ON employees_api_employee
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

-- clients_api_client
ALTER TABLE clients_api_client ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_clients ON clients_api_client
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

-- tenants_api_tenant (política especial)
ALTER TABLE tenants_api_tenant ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_tenants ON tenants_api_tenant
    FOR ALL TO PUBLIC
    USING (id = current_tenant_id() OR current_tenant_id() = 0);