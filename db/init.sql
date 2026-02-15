CREATE DATABASE trees;

USE trees; 
CREATE TABLE photo ( 
	id INTEGER AUTO_INCREMENT PRIMARY KEY, 
	photo VARCHAR(255) NOT NULL, 
	processed_photo VARCHAR(255), 
    txt VARCHAR(255),
	is_discovered boolean NOT NULL,
    photo_date DATETIME NOT NULL,
    modul boolean NOT NULL
);
USE trees; 
CREATE TABLE dataset (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    dataset VARCHAR(255) NOT NULL
);
USE trees; 
CREATE TABLE model (
    id INTEGER AUTO_INCREMENT PRIMARY KEY,
    model VARCHAR(255) NOT NULL
);