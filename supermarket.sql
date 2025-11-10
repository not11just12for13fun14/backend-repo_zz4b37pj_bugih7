-- Supermarket schema and seed for phpMyAdmin (MySQL/MariaDB)
-- Charset and SQL mode
SET NAMES utf8mb4;
SET time_zone = "+00:00";
SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';

-- Database (optional):
-- CREATE DATABASE IF NOT EXISTS supermarket CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE supermarket;

-- Drop tables if they exist (import-safe)
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

-- Categories
CREATE TABLE categories (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  slug VARCHAR(120) NOT NULL UNIQUE,
  icon VARCHAR(120) NULL,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Products
CREATE TABLE products (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  category_slug VARCHAR(120) NOT NULL,
  in_stock TINYINT(1) NOT NULL DEFAULT 1,
  image VARCHAR(500) NULL,
  rating DECIMAL(3,1) NULL DEFAULT 4.5,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_category_slug (category_slug),
  CONSTRAINT fk_products_category_slug FOREIGN KEY (category_slug) REFERENCES categories(slug)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Orders
CREATE TABLE orders (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  buyer_name VARCHAR(160) NOT NULL,
  buyer_email VARCHAR(160) NOT NULL,
  buyer_address TEXT NOT NULL,
  subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
  discount DECIMAL(12,2) NOT NULL DEFAULT 0,
  delivery_fee DECIMAL(12,2) NOT NULL DEFAULT 0,
  total DECIMAL(12,2) NOT NULL DEFAULT 0,
  status ENUM('pending','paid','shipped','completed','cancelled') NOT NULL DEFAULT 'pending',
  coupon_code VARCHAR(64) NULL,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Order Items
CREATE TABLE order_items (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id INT UNSIGNED NOT NULL,
  product_id VARCHAR(64) NULL,
  title VARCHAR(200) NOT NULL,
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  quantity INT UNSIGNED NOT NULL DEFAULT 1,
  image VARCHAR(500) NULL,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_order_id (order_id),
  CONSTRAINT fk_items_order_id FOREIGN KEY (order_id) REFERENCES orders(id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Seed categories
INSERT INTO categories (name, slug, icon) VALUES
  ('Buah & Sayur', 'produce', 'apple'),
  ('Daging & Protein', 'meat', 'beef'),
  ('Susu & Produk Dingin', 'dairy', 'milk'),
  ('Snack & Minuman', 'snacks', 'snack');

-- Seed products
INSERT INTO products (title, description, price, category_slug, in_stock, image, rating) VALUES
  ('Apel Fuji 1kg', 'Apel manis dan segar kualitas premium.', 35000.00, 'produce', 1, 'https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=800&q=80&auto=format&fit=crop', 4.7),
  ('Pisang Cavendish 1kg', 'Pisang matang siap makan.', 24000.00, 'produce', 1, 'https://images.unsplash.com/photo-1571772805064-207cd5b3e23d?w=800&q=80&auto=format&fit=crop', 4.5),
  ('Dada Ayam Fillet 500g', 'Daging ayam tanpa tulang.', 42000.00, 'meat', 1, 'https://images.unsplash.com/photo-1550332781-aecd27f7434b?w=800&q=80&auto=format&fit=crop', 4.6),
  ('Susu UHT 1L', 'Susu segar UHT full cream.', 18000.00, 'dairy', 1, 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80&auto=format&fit=crop', 4.4),
  ('Keripik Kentang 100g', 'Snack renyah rasa original.', 12000.00, 'snacks', 1, 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800&q=80&auto=format&fit=crop', 4.3);

-- Example order with items
INSERT INTO orders (buyer_name, buyer_email, buyer_address, subtotal, discount, delivery_fee, total, status, coupon_code)
VALUES ('Budi', 'budi@example.com', 'Jl. Mawar No. 1, Jakarta', 87000.00, 8700.00, 15000.00, 93300.00, 'pending', 'HEMAT10');

INSERT INTO order_items (order_id, product_id, title, price, quantity, image) VALUES
  (LAST_INSERT_ID(), 'mock-apple', 'Apel Fuji 1kg', 35000.00, 1, NULL),
  (LAST_INSERT_ID(), 'mock-chips', 'Keripik Kentang 100g', 12000.00, 2, NULL);

-- Done
