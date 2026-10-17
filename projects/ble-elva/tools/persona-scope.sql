BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='5s';
SET LOCAL search_path=pg_catalog;
SELECT json_build_object(
 'database',current_database(),'role',current_user,'read_only',current_setting('transaction_read_only'),
 'users',(SELECT count(*) FROM public.identity_users WHERE user_name=:'username'),
 'user_id',u.id,'username',u.user_name,'active',u.is_active,'admin',u.is_admin,'tenant_id',u.tenant_id,
 'tenant_active',EXISTS(SELECT 1 FROM public.tenants WHERE id=:'tenant_id'::uuid AND is_active),
 'plant_valid',EXISTS(SELECT 1 FROM public.workspace_plants WHERE id=:'plant_id'::uuid AND tenant_id=:'tenant_id'::uuid
   AND name=:'plant_name' AND site_number=:'site_number' AND is_active),
 'roles',(SELECT coalesce(json_agg(r.name ORDER BY r.name),'[]'::json)
   FROM public.security_user_roles ur JOIN public.security_roles r ON r.id=ur.role_id
   WHERE ur.user_id=u.id AND ur.is_active AND r.is_active),
 'permissions',(SELECT coalesce(json_agg(q.key ORDER BY q.key),'[]'::json) FROM
   (SELECT DISTINCT p.key FROM public.security_user_roles ur JOIN public.security_roles r ON r.id=ur.role_id
    JOIN public.security_role_permissions rp ON rp.role_id=r.id JOIN public.security_permissions p ON p.id=rp.permission_id
    WHERE ur.user_id=u.id AND ur.is_active AND r.is_active AND p.is_active) q),
 'scopes',(SELECT coalesce(json_agg(json_build_object('type',s.scope_type,'key',s.scope_key,
   'tenant_id',s.tenant_id,'plant_id',s.werk_id,'customer_id',s.customer_id,'laboratory_id',s.laboratory_id)
   ORDER BY s.scope_type),'[]'::json) FROM public.security_user_data_scopes s WHERE s.user_id=u.id AND s.is_active)
) FROM public.identity_users u WHERE u.user_name=:'username';
ROLLBACK;
