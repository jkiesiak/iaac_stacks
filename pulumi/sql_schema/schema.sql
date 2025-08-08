CREATE DATABASE database_rds;

-- Create the database_rds database and grant access to the postgres user
GRANT ALL PRIVILEGES ON DATABASE database_rds TO postgres;

-- Switch to the database_rds database
\c database_rds;

CREATE SCHEMA IF NOT EXISTS myschema1;
SET search_path TO myschema1,public;

CREATE TABLE  IF NOT EXISTS myschema1.customers (
    customer_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(15),
    address VARCHAR(100)
);

CREATE TABLE  IF NOT EXISTS myschema1.orders (
    order_id SERIAL PRIMARY KEY,
    order_date DATE,
    total_amount DECIMAL(10, 2),
    customer_id INTEGER REFERENCES myschema1.customers(customer_id),
    FOREIGN KEY (customer_id) REFERENCES myschema1.customers(customer_id)
);