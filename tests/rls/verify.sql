-- BE-11 / V-05 — Gate de Row Level Security con rol NO propietario.
-- Ejecutar con psql -v ON_ERROR_STOP=1 -f tests/rls/verify.sql contra una BD
-- migrada. Todo el script va en una transacción que se hace ROLLBACK: no deja
-- datos de prueba. Si alguna aserción falla, RAISE EXCEPTION aborta con exit!=0.
\set ON_ERROR_STOP on

BEGIN;

-- 1) Rol no propietario. Se crea aquí para que el gate sea autocontenido.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'auron_rls_probe') THEN
        CREATE ROLE auron_rls_probe LOGIN PASSWORD 'rls_probe_ci';
    END IF;
END $$;

GRANT USAGE ON SCHEMA public TO auron_rls_probe;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO auron_rls_probe;

-- 2) Comprobación estructural: RLS activo y al menos una policy por tabla.
DO $$
DECLARE
    t text;
    missing text := '';
    tables text[] := ARRAY[
        'appointments_api_appointment','audit_api_auditlog','billing_api_invoice',
        'clients_api_client','employees_api_commissionadjustment','employees_api_employee',
        'employees_api_liquidacion','employees_api_payrollconfiguration',
        'employees_api_regaliapascual','employees_api_vacation','inventory_api_product',
        'inventory_api_productcategory','inventory_api_supplier','mcp_api_tenantaicredential',
        'notifications_api_notificationtemplate','payments_api_azultransaction',
        'payments_api_payment','pos_api_cashregister','pos_api_coupon','pos_api_ncfsequence',
        'pos_api_posconfiguration','pos_api_promotion','pos_api_refundoperation','pos_api_sale',
        'services_api_service','services_api_servicecategory','settings_api_barbershopsettings',
        'settings_api_branch','settings_api_settingsauditlog','subscriptions_api_promotionalcredit',
        'subscriptions_api_subscription','support_api_supportticket','tenants_api_tenant',
        'pos_api_saledetail','inventory_api_stockmovement',
        'notifications_api_inappnotification'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_class c
                       WHERE c.relname = t AND c.relrowsecurity = true) THEN
            missing := missing || ' RLS_OFF:' || t;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_class c
                       WHERE c.relname = t AND c.relforcerowsecurity = true) THEN
            missing := missing || ' FORCE_OFF:' || t;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies p WHERE p.tablename = t) THEN
            missing := missing || ' NO_POLICY:' || t;
        END IF;
    END LOOP;
    IF missing <> '' THEN
        RAISE EXCEPTION 'RLS structural check failed:%', missing;
    END IF;
    RAISE NOTICE 'STRUCTURAL OK: 36 tablas con RLS, FORCE y policy';
END $$;

-- 3) Dos tenants y un cliente por tenant. Con FORCE ROW LEVEL SECURITY el
--    propietario también está sujeto a las policies: la siembra del gate usa
--    un bypass explícito y temporal, y se desactiva antes de las aserciones.
SET LOCAL app.tenant_id = '';
SET LOCAL app.rls_bypass = 'on';
INSERT INTO tenants_api_tenant
    (name, subdomain, locale, currency, date_format, time_zone, plan_type,
     subscription_status, trial_notifications_sent, billing_info, settings,
     max_employees, max_users, is_active, created_at, updated_at)
VALUES
    ('RLS Probe A', 'rls_probe_a', 'es-DO', 'DOP', 'dd/MM/yyyy', 'America/Santo_Domingo',
     '', 'trial', '{}', '{}', '{}', 5, 10, true, now(), now()),
    ('RLS Probe B', 'rls_probe_b', 'es-DO', 'DOP', 'dd/MM/yyyy', 'America/Santo_Domingo',
     '', 'trial', '{}', '{}', '{}', 5, 10, true, now(), now())
ON CONFLICT (subdomain) DO NOTHING;

SELECT id AS tenant_a FROM tenants_api_tenant WHERE subdomain = 'rls_probe_a' \gset
SELECT id AS tenant_b FROM tenants_api_tenant WHERE subdomain = 'rls_probe_b' \gset

INSERT INTO clients_api_client
    (tenant_id, full_name, notes, loyalty_points, is_active, created_at, updated_at)
VALUES
    (:tenant_a, 'Cliente RLS A', '', 0, true, now(), now()),
    (:tenant_b, 'Cliente RLS B', '', 0, true, now(), now());

SET LOCAL app.rls_probe_other = :tenant_b;
SET LOCAL app.rls_bypass = 'off';

SET ROLE auron_rls_probe;

-- 4) Sin contexto: 0 filas en tabla de negocio y en la tabla Tenant.
SET LOCAL app.tenant_id = '';
SET LOCAL app.rls_bypass = 'off';
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM clients_api_client;
    IF n <> 0 THEN RAISE EXCEPTION 'FAIL_NO_CONTEXT_CLIENTS: %', n; END IF;
    SELECT count(*) INTO n FROM tenants_api_tenant;
    IF n <> 0 THEN RAISE EXCEPTION 'FAIL_NO_CONTEXT_TENANTS: %', n; END IF;
    RAISE NOTICE 'FAIL_CLOSED OK';
END $$;

-- 5) Con contexto del tenant A: ve sólo lo suyo; el UPDATE/DELETE cross-tenant
--    afecta 0 filas y el INSERT cross-tenant es rechazado por WITH CHECK.
SET LOCAL app.tenant_id = :tenant_a;
DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM clients_api_client;
    IF n <> 1 THEN RAISE EXCEPTION 'FAIL_TENANT_A_VISIBILITY: %', n; END IF;
    SELECT count(*) INTO n FROM clients_api_client
        WHERE tenant_id = current_setting('app.rls_probe_other')::bigint;
    IF n <> 0 THEN RAISE EXCEPTION 'FAIL_CROSS_TENANT_READ: %', n; END IF;
    SELECT count(*) INTO n FROM tenants_api_tenant;
    IF n <> 1 THEN RAISE EXCEPTION 'FAIL_TENANT_A_TENANT_ROW: %', n; END IF;

    UPDATE clients_api_client SET full_name = 'HACK'
        WHERE tenant_id = current_setting('app.rls_probe_other')::bigint;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 0 THEN RAISE EXCEPTION 'FAIL_CROSS_TENANT_UPDATE: %', n; END IF;

    DELETE FROM clients_api_client
        WHERE tenant_id = current_setting('app.rls_probe_other')::bigint;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 0 THEN RAISE EXCEPTION 'FAIL_CROSS_TENANT_DELETE: %', n; END IF;

    BEGIN
        INSERT INTO clients_api_client
            (tenant_id, full_name, notes, loyalty_points, is_active, created_at, updated_at)
        VALUES
            (current_setting('app.rls_probe_other')::bigint, 'HACK', '', 0, true, now(), now());
        RAISE EXCEPTION 'FAIL_CROSS_TENANT_INSERT_ALLOWED';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;  -- esperado: WITH CHECK rechaza la fila de otro tenant
    END;
    RAISE NOTICE 'ISOLATION OK: SELECT/INSERT/UPDATE/DELETE cross-tenant bloqueados';
END $$;

-- 6) Bypass explícito del servidor: ve los 2 clientes. Sólo se activa desde
--    el middleware para superuser/webhooks, nunca desde payload del cliente.
SET LOCAL app.rls_bypass = 'on';
DO $$
DECLARE n integer;
BEGIN
    -- Sólo las filas sembradas por este gate: la BD puede tener datos de E2E.
    SELECT count(*) INTO n FROM clients_api_client
        WHERE full_name IN ('Cliente RLS A', 'Cliente RLS B');
    IF n <> 2 THEN RAISE EXCEPTION 'FAIL_BYPASS: %', n; END IF;
    RAISE NOTICE 'BYPASS OK';
END $$;

RESET ROLE;
ROLLBACK;

\echo 'RLS VERIFY: ALL CHECKS PASSED'
