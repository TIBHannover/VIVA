-- Add users
INSERT INTO public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES (1, 'pbkdf2_sha256$150000$3aGdeqfDrQRe$kSFGSQsU4gQNy47ETQUe/4h10BomG185PtLMTmgdyhc=', '2019-07-22 13:32:48.991608', false, 'test', 'Max', 'Mustermann', 'max@test.de', false, true, '2019-07-22 11:39:40.630843');
INSERT INTO public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES (2, 'pbkdf2_sha256$150000$Cmd3V6WoQe0k$EsUUGnmqTj6LauphU+cYcxMaYJUtyLrT4eL9pRS/C9Q=', null, false, 'anonym', 'Arno', 'Nühm', 'arno@test.de', false, true, '2019-07-23 10:53:02.085431');

-- Add user / role relations
INSERT INTO public.auth_user_groups (id, user_id, group_id) VALUES (1, 1, 1);
INSERT INTO public.auth_user_groups (id, user_id, group_id) VALUES (2, 1, 2);
INSERT INTO public.auth_user_groups (id, user_id, group_id) VALUES (3, 1, 3);
INSERT INTO public.auth_user_groups (id, user_id, group_id) VALUES (4, 2, 2);

-- Update sequences
SELECT setval(pg_get_serial_sequence('"auth_user"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_user";
SELECT setval(pg_get_serial_sequence('"auth_group"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_group";
SELECT setval(pg_get_serial_sequence('"auth_user_groups"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_user_groups";
SELECT setval(pg_get_serial_sequence('"auth_group_description"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_group_description";
