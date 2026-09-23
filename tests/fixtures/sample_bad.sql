-- sqlfluff:dialect:mysql
SELECT id FROM users UNION SELECT name FROM admins LIMIT 10;
SELECT * FROM orders WHERE id = NULL;
