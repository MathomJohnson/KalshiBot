-- RLS policies call is_allowed_user(); authenticated role needs EXECUTE.
GRANT EXECUTE ON FUNCTION public.is_allowed_user() TO authenticated;
