-- Add demo user
INSERT INTO public.auth_user (password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES ('pbkdf2_sha256$150000$8EMQikoJGZnZ$X47bAmUfLAoP28HcXRL+3TC6GdJZ+hUmwJaHcCoHiTo=', null, false, 'vivademo', 'Viva', 'Demo', 'demo@viva.de', false, true, '2019-07-23 10:53:02.085431');

-- Disable all other users
UPDATE public.auth_user SET is_active = false WHERE username != 'vivademo';

-- Add new user to all roles
INSERT INTO public.auth_user_groups (user_id, group_id) SELECT auth_user.id, auth_group.id from public.auth_user, public.auth_group where auth_user.username = 'vivademo';
