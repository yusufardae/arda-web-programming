CREATE DATABASE IF NOT EXISTS mars_gym
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY 'MarsApp123!';
ALTER USER 'root'@'localhost' IDENTIFIED BY 'MarsApp123!';

CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY 'MarsApp123!';
ALTER USER 'root'@'127.0.0.1' IDENTIFIED BY 'MarsApp123!';

GRANT ALL PRIVILEGES ON mars_gym.* TO 'root'@'localhost';
GRANT ALL PRIVILEGES ON mars_gym.* TO 'root'@'127.0.0.1';
FLUSH PRIVILEGES;

USE mars_gym;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    telephone VARCHAR(30) NOT NULL,
    gender VARCHAR(20) NOT NULL,
    date_of_birth DATE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    terms_accepted TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS membership_selections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    membership_code VARCHAR(10) NULL UNIQUE,
    club VARCHAR(30) NOT NULL,
    gym_access VARCHAR(30) NOT NULL,
    pool_selected TINYINT(1) NOT NULL DEFAULT 0,
    classes_selected TINYINT(1) NOT NULL DEFAULT 0,
    massage_selected TINYINT(1) NOT NULL DEFAULT 0,
    physiotherapy_selected TINYINT(1) NOT NULL DEFAULT 0,
    joining_fee DECIMAL(10, 2) NOT NULL,
    gym_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    pool_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    classes_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    massage_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    physiotherapy_fee DECIMAL(10, 2) NOT NULL DEFAULT 0,
    discount_rate DECIMAL(5, 2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
    total_price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_membership_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

USE mars_gym;
SELECT * FROM membership_selections;

SELECT id, name, surname, email, telephone
FROM users;





USE mars_gym;

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE membership_selections;
TRUNCATE TABLE users;

SET FOREIGN_KEY_CHECKS = 1;