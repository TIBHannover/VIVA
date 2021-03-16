-- Add roles
INSERT INTO public.auth_group (id, name) VALUES (1, 'User manager');
INSERT INTO public.auth_group (id, name) VALUES (2, 'Annotator');
INSERT INTO public.auth_group (id, name) VALUES (3, 'Trainer');

-- Add role descriptions
INSERT INTO public.auth_group_description (id, description, group_id) VALUES (1, 'User able to create, update and delete other users.', 1);
INSERT INTO public.auth_group_description (id, description, group_id) VALUES (2, 'User able to annotate data.', 2);
INSERT INTO public.auth_group_description (id, description, group_id) VALUES (3, 'User able to train a neural net.', 3);

-- Add base collections
INSERT INTO public.collection (id, basepath, description, name) VALUES (1, 'webcrawler', 'Collection of images added by webcrawler', 'Webcrawler');
INSERT INTO public.collection (id, basepath, description, name) VALUES (2, 'upload', 'Collection of images added by upload', 'Upload');

-- Add base class types
INSERT INTO public.classtype (id, name, description) VALUES (1, 'Concept', 'This is an image concept');
INSERT INTO public.classtype (id, name, description) VALUES (2, 'Person', 'This is a person');

-- INIT sequences
SELECT setval(pg_get_serial_sequence('"auth_user"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_user";
SELECT setval(pg_get_serial_sequence('"auth_group"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_group";
SELECT setval(pg_get_serial_sequence('"auth_user_groups"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_user_groups";
SELECT setval(pg_get_serial_sequence('"auth_group_description"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "auth_group_description";

SELECT setval(pg_get_serial_sequence('"bboxannotation"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "bboxannotation";
SELECT setval(pg_get_serial_sequence('"collection"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "collection";
SELECT setval(pg_get_serial_sequence('"class"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "class";
SELECT setval(pg_get_serial_sequence('"classtype"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "classtype";
SELECT setval(pg_get_serial_sequence('"evaluation"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "evaluation";
SELECT setval(pg_get_serial_sequence('"image"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "image";
SELECT setval(pg_get_serial_sequence('"imageannotation"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "imageannotation";
SELECT setval(pg_get_serial_sequence('"imageprediction"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "imageprediction";
SELECT setval(pg_get_serial_sequence('"model"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "model";
SELECT setval(pg_get_serial_sequence('"video"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "video";
SELECT setval(pg_get_serial_sequence('"videoframe"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "videoframe";
SELECT setval(pg_get_serial_sequence('"videoshot"','id'), coalesce(max("id"), 1), max("id") IS NOT null) FROM "videoshot";
