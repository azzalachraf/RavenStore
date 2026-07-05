insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('product-files', 'product-files', false, 26214400, array['application/pdf', 'application/zip']),
  ('product-images', 'product-images', true, 10485760, array['image/jpeg', 'image/png', 'image/webp']),
  ('backups', 'backups', false, null, null)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- All writes use the backend service-role key. No client write policy is intentionally created.
