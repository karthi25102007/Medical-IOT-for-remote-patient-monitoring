-- Medical IoT — MySQL Workbench schema
-- Run this in MySQL Workbench (copy-paste into a query tab + Execute),
-- OR just run the website: python app.py  (it creates everything automatically).

CREATE DATABASE IF NOT EXISTS medical_iot
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE medical_iot;

CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(20) NOT NULL,
    `condition` VARCHAR(200) DEFAULT '',
    device_id VARCHAR(50) UNIQUE NOT NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS vitals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    `timestamp` DATETIME NOT NULL,
    heart_rate INT NOT NULL,
    spo2 DECIMAL(4,1) NOT NULL,
    temperature DECIMAL(4,1) NOT NULL,
    bp_systolic INT NOT NULL,
    bp_diastolic INT NOT NULL,
    CONSTRAINT fk_vitals_patient FOREIGN KEY (patient_id)
        REFERENCES patients(id) ON DELETE CASCADE,
    INDEX idx_vitals_patient_time (patient_id, `timestamp` DESC)
) ENGINE=InnoDB;
