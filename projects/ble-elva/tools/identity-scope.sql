BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL search_path=pg_catalog;
SELECT json_build_object(
 'database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'),
 'users',(SELECT count(*) FROM public.identity_users WHERE user_name=:'username'),
 'user_id',u.id,'username',u.user_name,'active',u.is_active,'admin',u.is_admin,'tenant_id',u.tenant_id,
 'tenant_active',EXISTS(SELECT 1 FROM public.tenants WHERE id=:'tenant_id'::uuid AND is_active),
 'laboratory_role',EXISTS(SELECT 1 FROM public.security_user_roles ur JOIN public.security_roles r ON r.id=ur.role_id
   WHERE ur.user_id=u.id AND ur.is_active AND r.is_active AND r.name='Laborleiter'),
 'product_permission',EXISTS(SELECT 1 FROM public.security_user_roles ur JOIN public.security_roles r ON r.id=ur.role_id
   JOIN public.security_role_permissions rp ON rp.role_id=r.id JOIN public.security_permissions p ON p.id=rp.permission_id
   WHERE ur.user_id=u.id AND ur.is_active AND r.is_active AND r.name='Laborleiter' AND p.is_active AND p.key='products.manage'),
 'plant_valid',EXISTS(SELECT 1 FROM public.workspace_plants WHERE id=:'plant_id'::uuid AND tenant_id=:'tenant_id'::uuid
   AND name=:'plant_name' AND site_number=:'site_number' AND is_active),
 'expected_plant_scopes',(SELECT count(*) FROM public.security_user_data_scopes WHERE user_id=u.id AND is_active
   AND scope_type='Plant' AND scope_key=:'plant_id' AND werk_id=:'plant_id'::uuid AND tenant_id=:'tenant_id'::uuid
   AND customer_id IS NULL AND laboratory_id IS NULL),
 'plant_scopes',(SELECT count(*) FROM public.security_user_data_scopes WHERE user_id=u.id AND is_active AND scope_type='Plant'),
 'global_scopes',(SELECT count(*) FROM public.security_user_data_scopes WHERE user_id=u.id AND is_active AND scope_type='Global'),
 'tenant_scopes',(SELECT count(*) FROM public.security_user_data_scopes WHERE user_id=u.id AND is_active
   AND scope_type='Tenant' AND scope_key=:'tenant_id' AND tenant_id=:'tenant_id'::uuid
   AND werk_id IS NULL AND customer_id IS NULL AND laboratory_id IS NULL),
 'all_scopes',(SELECT count(*) FROM public.security_user_data_scopes WHERE user_id=u.id AND is_active)
) FROM public.identity_users u WHERE u.user_name=:'username';
ROLLBACK;
