-- Créer la base de présence
CREATE DATABASE IF NOT EXISTS rhunigom_presence CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Créer la base de production
CREATE DATABASE IF NOT EXISTS rhunigom__database_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Créer l'utilisateur
CREATE USER IF NOT EXISTS 'rhunigom_presence_users'@'%' IDENTIFIED BY 'password';

-- Donner les privilèges
GRANT ALL PRIVILEGES ON rhunigom_presence.* TO 'rhunigom_presence_users'@'%';
GRANT ALL PRIVILEGES ON rhunigom__database_production.* TO 'rhunigom_presence_users'@'%';

FLUSH PRIVILEGES;
