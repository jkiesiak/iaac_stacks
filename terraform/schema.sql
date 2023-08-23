CREATE SCHEMA IF NOT EXISTS schema_1;
CREATE DATABASE "database";
USE schema_1;

CREATE TABLE "database"."customers" (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(15),
    address VARCHAR(100)
);

