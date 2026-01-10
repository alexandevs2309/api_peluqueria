-- PostgreSQL Row Level Security Setup
-- Ejecutar DESPUÉS de migraciones Django

-- 1. Habilitar RLS en tablas críticas
ALTER TABLE auth_api_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees_api_employee ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients_api_client ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos_api_sale ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_api_payrollsettlement ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees_api_earning ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants_api_tenant ENABLE ROW LEVEL SECURITY;

-- 2. Crear función para obtener tenant_id actual
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(current_setting('app.current_tenant_id', true)::INTEGER, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- 3. Políticas RLS por tabla
CREATE POLICY tenant_isolation_users ON auth_api_user
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

CREATE POLICY tenant_isolation_employees ON employees_api_employee
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

CREATE POLICY tenant_isolation_clients ON clients_api_client
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

CREATE POLICY tenant_isolation_sales ON pos_api_sale
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

CREATE POLICY tenant_isolation_settlements ON payroll_api_payrollsettlement
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

CREATE POLICY tenant_isolation_earnings ON employees_api_earning
    FOR ALL TO PUBLIC
    USING (tenant_id = current_tenant_id() OR current_tenant_id() = 0);

-- Política especial para tenants (solo propietarios pueden ver su tenant)
CREATE POLICY tenant_isolation_tenants ON tenants_api_tenant
    FOR ALL TO PUBLIC
    USING (id = current_tenant_id() OR current_tenant_id() = 0);