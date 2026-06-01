-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: restaurant_db
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cart`
--

DROP TABLE IF EXISTS `cart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cart` (
  `cart_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int DEFAULT NULL,
  `item_id` int DEFAULT NULL,
  `quantity` int DEFAULT '1',
  `added_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`cart_id`),
  KEY `customer_id` (`customer_id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `cart_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `cart_ibfk_2` FOREIGN KEY (`item_id`) REFERENCES `menu` (`item_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cart`
--

LOCK TABLES `cart` WRITE;
/*!40000 ALTER TABLE `cart` DISABLE KEYS */;
/*!40000 ALTER TABLE `cart` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `categories`
--

DROP TABLE IF EXISTS `categories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `categories` (
  `category_id` int NOT NULL AUTO_INCREMENT,
  `category_name` varchar(100) NOT NULL,
  `status` enum('Active','Inactive') DEFAULT 'Active',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`category_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `categories`
--

LOCK TABLES `categories` WRITE;
/*!40000 ALTER TABLE `categories` DISABLE KEYS */;
INSERT INTO `categories` VALUES (1,'Main Course','Active','2026-02-16 11:08:35'),(2,'Desserts','Active','2026-02-16 11:08:35'),(3,'Beverages','Active','2026-02-16 11:08:35');
/*!40000 ALTER TABLE `categories` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `customers`
--

DROP TABLE IF EXISTS `customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customers` (
  `customer_id` int NOT NULL AUTO_INCREMENT,
  `customer_name` varchar(100) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `latitude` decimal(10,8) DEFAULT NULL,
  `longitude` decimal(11,8) DEFAULT NULL,
  PRIMARY KEY (`customer_id`),
  KEY `fk_customer_user` (`user_id`),
  CONSTRAINT `fk_customer_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `customers`
--

LOCK TABLES `customers` WRITE;
/*!40000 ALTER TABLE `customers` DISABLE KEYS */;
INSERT INTO `customers` VALUES (1,'om ingole','ingoleom38@gmail.com','9307170583',1,22.35111480,78.66774280);
/*!40000 ALTER TABLE `customers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employee_details`
--

DROP TABLE IF EXISTS `employee_details`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employee_details` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `employee_type` varchar(50) NOT NULL,
  `joining_date` date DEFAULT NULL,
  `shift` varchar(50) DEFAULT NULL,
  `salary` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `employee_details_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employee_details`
--

LOCK TABLES `employee_details` WRITE;
/*!40000 ALTER TABLE `employee_details` DISABLE KEYS */;
INSERT INTO `employee_details` VALUES (1,2,'Delivery Boy','2026-04-16','Night',NULL),(2,3,'Waiter','2026-04-16','Afternoon',NULL),(3,4,'Cook','2026-04-16','Morning',NULL);
/*!40000 ALTER TABLE `employee_details` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `employee_tasks`
--

DROP TABLE IF EXISTS `employee_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `employee_tasks` (
  `task_id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int DEFAULT NULL,
  `order_id` int DEFAULT NULL,
  `task_type` enum('Cook','Serve','Deliver') DEFAULT NULL,
  `status` enum('Pending','Completed') DEFAULT 'Pending',
  `assigned_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `employee_tasks`
--

LOCK TABLES `employee_tasks` WRITE;
/*!40000 ALTER TABLE `employee_tasks` DISABLE KEYS */;
/*!40000 ALTER TABLE `employee_tasks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `menu`
--

DROP TABLE IF EXISTS `menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `menu` (
  `item_id` int NOT NULL AUTO_INCREMENT,
  `item_name` varchar(150) NOT NULL,
  `description` text,
  `price` decimal(10,2) NOT NULL,
  `category_id` int DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  `status` enum('Available','Unavailable') DEFAULT 'Available',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `stock` int DEFAULT '0',
  PRIMARY KEY (`item_id`),
  KEY `category_id` (`category_id`),
  CONSTRAINT `menu_ibfk_1` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu`
--

LOCK TABLES `menu` WRITE;
/*!40000 ALTER TABLE `menu` DISABLE KEYS */;
INSERT INTO `menu` VALUES (1,'Paneer Butter Masala','Creamy tomato based curry',220.00,1,'9bc9d07a-0348-4697-9d5e-cb705a7c189a.jpg','Available','2026-02-16 11:08:35',0),(2,'Chicken Biryani','Spicy layered rice dish',200.00,1,'35b0625e-cc6b-4f15-acad-3fa05f60ee01.jpg','Available','2026-02-16 11:08:35',0),(3,'Chocolate Dessert','Rich chocolate cake',250.00,2,'1e241087-816c-42fc-a541-b631d3222b49.jpg','Available','2026-02-16 11:08:35',0),(4,'Cold Coffe','Chilled coffee with ice cream',210.00,3,'ccf54d40-a8e6-4089-9e20-d6090a712f36.jpg','Available','2026-02-16 11:08:35',0);
/*!40000 ALTER TABLE `menu` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifications` (
  `id` int NOT NULL AUTO_INCREMENT,
  `employee_id` int NOT NULL,
  `message` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `employee_id` (`employee_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`employee_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `notifications`
--

LOCK TABLES `notifications` WRITE;
/*!40000 ALTER TABLE `notifications` DISABLE KEYS */;
INSERT INTO `notifications` VALUES (2,26,'New table booking for Table None on None at None','2026-03-17 12:20:49'),(3,26,'New table booking for Table 92 on 2026-03-17 at 15:18','2026-03-17 15:16:57'),(4,26,'New table booking for Table 53 on 2026-03-31 at 02:40','2026-03-27 14:41:08'),(5,26,'New table booking for Table 53 on 2026-04-04 at 08:56','2026-04-01 16:54:32'),(6,26,'New table booking for Table 92 on 2026-04-01 at 17:00','2026-04-01 16:58:48'),(7,26,'New table booking for Table 53 on 2026-04-15 at 14:00','2026-04-15 13:42:39'),(8,26,'New table booking for Table 53 on 2026-04-08 at 15:00','2026-04-15 14:21:15'),(9,26,'New table booking for Table 92 on 2026-04-15 at 15:00','2026-04-15 14:48:58'),(10,26,'New table booking for Table 53 on 2026-04-16 at 00:00','2026-04-15 23:43:49'),(11,26,'New table booking for Table 92 on 2026-04-16 at 13:00','2026-04-16 11:21:33'),(12,1,'New table booking for Table 92 on 2026-04-17 at 14:00','2026-04-16 14:54:51'),(13,1,'New table booking for Table 54 on 2026-04-16 at 15:00','2026-04-16 14:58:18');
/*!40000 ALTER TABLE `notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_items`
--

DROP TABLE IF EXISTS `order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_items` (
  `order_item_id` int NOT NULL AUTO_INCREMENT,
  `order_id` int DEFAULT NULL,
  `item_id` int DEFAULT NULL,
  `quantity` int NOT NULL,
  `price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`order_item_id`),
  KEY `fk_order_items_order` (`order_id`),
  KEY `fk_order_items_menu` (`item_id`),
  CONSTRAINT `fk_order_items_menu` FOREIGN KEY (`item_id`) REFERENCES `menu` (`item_id`),
  CONSTRAINT `fk_order_items_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`order_id`) ON DELETE CASCADE,
  CONSTRAINT `order_items_ibfk_2` FOREIGN KEY (`item_id`) REFERENCES `menu` (`item_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_items`
--

LOCK TABLES `order_items` WRITE;
/*!40000 ALTER TABLE `order_items` DISABLE KEYS */;
INSERT INTO `order_items` VALUES (1,1,4,1,210.00),(2,2,1,2,220.00),(3,2,2,2,200.00);
/*!40000 ALTER TABLE `order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `order_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int DEFAULT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `payment_method` enum('Cash','Card','UPI') DEFAULT 'Cash',
  `payment_status` enum('Pending','Paid','Failed') DEFAULT 'Pending',
  `status` enum('Pending','Cooking','Ready','Served','Completed','Delivering','Delivered','Cancelled') NOT NULL DEFAULT 'Pending',
  `order_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `latitude` decimal(10,8) DEFAULT NULL,
  `longitude` decimal(11,8) DEFAULT NULL,
  `cook_id` int DEFAULT NULL,
  `waiter_id` int DEFAULT NULL,
  `delivery_id` int DEFAULT NULL,
  `order_type` enum('Online','Table') DEFAULT 'Online',
  `table_id` int DEFAULT NULL,
  `assigned_employee` int DEFAULT NULL,
  `razorpay_order_id` varchar(255) DEFAULT NULL,
  `razorpay_payment_id` varchar(255) DEFAULT NULL,
  `delivery_address` text,
  `delivery_otp` varchar(6) DEFAULT NULL,
  PRIMARY KEY (`order_id`),
  KEY `fk_employee_order` (`assigned_employee`),
  KEY `fk_orders_customer` (`customer_id`),
  KEY `fk_orders_cook` (`cook_id`),
  KEY `fk_orders_waiter` (`waiter_id`),
  KEY `fk_orders_delivery` (`delivery_id`),
  KEY `fk_orders_table` (`table_id`),
  CONSTRAINT `fk_employee_order` FOREIGN KEY (`assigned_employee`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_order_cook` FOREIGN KEY (`cook_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_order_customer` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_order_delivery` FOREIGN KEY (`delivery_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_order_waiter` FOREIGN KEY (`waiter_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_orders_cook` FOREIGN KEY (`cook_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_orders_customer` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_orders_delivery` FOREIGN KEY (`delivery_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_orders_table` FOREIGN KEY (`table_id`) REFERENCES `restaurant_tables` (`table_id`),
  CONSTRAINT `fk_orders_waiter` FOREIGN KEY (`waiter_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
INSERT INTO `orders` VALUES (1,1,210.00,'UPI','Paid','Delivered','2026-04-16 09:17:52',20.95029100,77.76437350,4,NULL,2,'Online',NULL,NULL,'order_Se6zVnMb3I1Jp6','pay_Se6zcZMJSTkAiw','Flat 203, Cotton Green Colony No-01, Amravati, Maharashtra - 444600, India',NULL),(2,1,840.00,'UPI','Paid','Served','2026-04-16 09:29:53',NULL,NULL,4,3,NULL,'Table',54,NULL,'order_Se7C8K6LupXsrC','pay_Se7CHsR3psD1b0',NULL,NULL);
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `restaurant_tables`
--

DROP TABLE IF EXISTS `restaurant_tables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `restaurant_tables` (
  `table_id` int NOT NULL AUTO_INCREMENT,
  `table_number` int DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `status` varchar(20) DEFAULT 'Available',
  `price_per_person` decimal(10,2) NOT NULL DEFAULT '100.00',
  `photo` varchar(255) DEFAULT 'default_table.jpg',
  PRIMARY KEY (`table_id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `restaurant_tables`
--

LOCK TABLES `restaurant_tables` WRITE;
/*!40000 ALTER TABLE `restaurant_tables` DISABLE KEYS */;
INSERT INTO `restaurant_tables` VALUES (53,1,30,'Available',150.00,'table_1_aa906682.webp'),(54,2,30,'Available',150.00,'table_2_9879c621.webp'),(55,3,30,'Available',150.00,'table_3_c5177ae3.webp'),(56,4,30,'Available',150.00,'table_4_5c762e2f.webp'),(57,5,30,'Available',150.00,'table_5_3b99b436.webp'),(58,6,25,'Available',140.00,'table_6_dfda44a1.webp'),(59,7,25,'Available',140.00,'table_7_f4c686c9.webp'),(60,8,25,'Available',140.00,'table_8_b5343989.webp'),(61,9,25,'Available',140.00,'table_9.jpg'),(62,10,25,'Available',140.00,'table_10.jpg'),(63,11,20,'Available',120.00,'table_11.jpg'),(64,12,20,'Available',120.00,'table_12.jpg'),(65,13,20,'Available',120.00,'table_13.jpg'),(66,14,20,'Available',120.00,'table_14.jpg'),(67,15,20,'Available',120.00,'table_15.jpg'),(68,16,15,'Available',100.00,'table_16.jpg'),(69,17,15,'Available',100.00,'table_17.jpg'),(70,18,15,'Available',100.00,'table_18.jpg'),(71,19,15,'Available',100.00,'table_19.jpg'),(72,20,15,'Available',100.00,'table_20.jpg'),(73,21,10,'Available',80.00,'table_21.jpg'),(74,22,10,'Available',80.00,'table_22.jpg'),(75,23,10,'Available',80.00,'table_23.jpg'),(76,24,10,'Available',80.00,'table_24.jpg'),(77,25,10,'Available',80.00,'table_25.jpg'),(78,26,10,'Available',80.00,'table_26.jpg'),(79,27,10,'Available',80.00,'table_27.jpg'),(80,28,10,'Available',80.00,'table_28.jpg'),(81,29,10,'Available',80.00,'table_29.jpg'),(82,30,10,'Available',80.00,'table_30.jpg'),(83,31,5,'Available',50.00,'table_31.jpg'),(84,32,5,'Available',50.00,'table_32.jpg'),(85,33,5,'Available',50.00,'table_33.jpg'),(86,34,5,'Available',50.00,'table_34.jpg'),(87,35,5,'Available',50.00,'table_35.jpg'),(88,36,2,'Available',30.00,'table_36.jpg'),(89,37,2,'Available',30.00,'table_37.jpg'),(90,38,2,'Available',30.00,'table_38.jpg'),(91,39,2,'Available',30.00,'table_39.jpg'),(92,40,2,'Available',30.00,'table_40.jpg');
/*!40000 ALTER TABLE `restaurant_tables` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `salaries`
--

DROP TABLE IF EXISTS `salaries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `salaries` (
  `salary_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `year` int NOT NULL,
  `month` int NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `status` enum('Paid','Pending') DEFAULT 'Pending',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `bonus` decimal(10,2) DEFAULT '0.00',
  PRIMARY KEY (`salary_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `salaries_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `salaries`
--

LOCK TABLES `salaries` WRITE;
/*!40000 ALTER TABLE `salaries` DISABLE KEYS */;
INSERT INTO `salaries` VALUES (1,2,2026,4,20001.00,'Paid','2026-04-16 07:14:59',1.00),(2,2,2026,3,20500.00,'Paid','2026-04-16 07:24:37',500.00),(3,5,2026,4,50000.00,'Paid','2026-04-16 07:59:47',500.00),(4,4,2026,1,20000.00,'Paid','2026-04-16 08:02:47',5.00),(5,4,2026,4,20000.00,'Paid','2026-04-16 08:03:15',50.00);
/*!40000 ALTER TABLE `salaries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `table_bookings`
--

DROP TABLE IF EXISTS `table_bookings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `table_bookings` (
  `booking_id` int NOT NULL AUTO_INCREMENT,
  `customer_id` int DEFAULT NULL,
  `table_id` int DEFAULT NULL,
  `waiter_id` int DEFAULT NULL,
  `booking_date` date DEFAULT NULL,
  `booking_time` time DEFAULT NULL,
  `guests` int DEFAULT NULL,
  `booking_status` varchar(20) DEFAULT 'Booked',
  `payment_status` varchar(20) DEFAULT 'Pending',
  `total_price` decimal(10,2) DEFAULT NULL,
  `razorpay_order_id` varchar(255) DEFAULT NULL,
  `razorpay_payment_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`booking_id`),
  KEY `fk_booking_customer` (`customer_id`),
  KEY `fk_booking_waiter` (`waiter_id`),
  KEY `fk_booking_table` (`table_id`),
  CONSTRAINT `fk_booking_customer` FOREIGN KEY (`customer_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_booking_table` FOREIGN KEY (`table_id`) REFERENCES `restaurant_tables` (`table_id`),
  CONSTRAINT `fk_booking_waiter` FOREIGN KEY (`waiter_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `table_bookings`
--

LOCK TABLES `table_bookings` WRITE;
/*!40000 ALTER TABLE `table_bookings` DISABLE KEYS */;
INSERT INTO `table_bookings` VALUES (1,1,92,NULL,'2026-04-17','14:00:00',2,'Booked','Paid',60.00,'order_Se76pgegYvZiUF','pay_Se76yfcXA1HaO0'),(2,1,54,NULL,'2026-04-16','15:00:00',29,'Booked','Paid',3915.00,'order_Se7AYvGL8rKqSv','pay_Se7Af5qI2Ivumx');
/*!40000 ALTER TABLE `table_bookings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `photo` longblob,
  `email` varchar(100) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `role` enum('SuperAdmin','Manager','Employee','Customer') NOT NULL,
  `status` enum('Active','Inactive','Suspended') DEFAULT 'Active',
  `phone` varchar(15) DEFAULT NULL,
  `address` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `salary` decimal(10,2) DEFAULT NULL,
  `is_guest` tinyint(1) DEFAULT '1',
  `current_latitude` double DEFAULT NULL,
  `current_longitude` double DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `unique_phone` (`phone`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'om ingole',NULL,'ingoleom38@gmail.com','scrypt:32768:8:1$vQAVRtJUYycwtXor$058a42418ad8526c74976e18a036cdfdfc2b7d703e238862466b4e6626a70a5e3a166258603789936dab52d60bec19121b1eb61c6baa54da8084e68e14648312','Customer','Active','9307170583','P.O. GHATLADKI TAL. CHANDURBAZAR DIST. AMRAVATI','2026-04-16 06:25:32',NULL,1,NULL,NULL),(2,'Jay Joshi',NULL,'jay@gmail.com','scrypt:32768:8:1$3v1uuy5vSN5dbutv$3ead928b010d90e1fd96f074e6ec23b3f3f430bf60154385bef0dc44863856f422c251b7e2f4428096e6d09f732c0d8b87df0a7014a69d683a3c650fed0a037c','Employee','Active','1234567890','Amravati','2026-04-16 07:09:37',20000.00,1,NULL,NULL),(3,'ABHAY',NULL,'abhay@gmail.com','scrypt:32768:8:1$XUPOXI9J85DylfOQ$38c92d509a59653bbed387917251b05fa927c074e05d9b06c74f8b085c86e8b811a4c395aaefaf1ea30175544d97f653f206bcb7c1407e8cd0bf1089a091c6a5','Employee','Active','9635852074','amravati','2026-04-16 07:34:19',20000.00,1,NULL,NULL),(4,'siya',NULL,'siya@gmail.com','scrypt:32768:8:1$e4CFqClRG9AJVcGd$d7de6868a102668d2a9f3b8ac1998473b82b561dc11b3ae44464c360d861b60b5ed78311fa6d22d12be095960219c540c4e20d3ba669d26a0db833e5e9c1bc58','Employee','Active','8529637410','amravati','2026-04-16 07:35:50',20000.00,1,NULL,NULL),(5,'abhishekh',NULL,'abhi@gmail.com','scrypt:32768:8:1$Ig1NNufM4Y3SWwqV$bbf4beae32039766cd179f5195b606726c1ae3955780883ad2489f41272b0540fb1ba1cb4a532a2944d5175d2d36d869da7d731489c7e6b36ddc87cae90bec1c','Manager','Active','7894612305','P.O. GHATLADKI TAL. CHANDURBAZAR DIST. AMRAVATI','2026-04-16 07:37:11',50000.00,1,NULL,NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `visitor_order_items`
--

DROP TABLE IF EXISTS `visitor_order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visitor_order_items` (
  `item_id` int NOT NULL AUTO_INCREMENT,
  `order_id` int DEFAULT NULL,
  `menu_item_id` int DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  `price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`item_id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `visitor_order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `visitor_orders` (`order_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `visitor_order_items`
--

LOCK TABLES `visitor_order_items` WRITE;
/*!40000 ALTER TABLE `visitor_order_items` DISABLE KEYS */;
INSERT INTO `visitor_order_items` VALUES (1,1,1,1,220.00),(2,1,2,1,200.00),(3,2,2,1,200.00),(4,2,3,1,250.00);
/*!40000 ALTER TABLE `visitor_order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `visitor_orders`
--

DROP TABLE IF EXISTS `visitor_orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `visitor_orders` (
  `order_id` int NOT NULL AUTO_INCREMENT,
  `customer_name` varchar(100) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `table_no` varchar(20) DEFAULT NULL,
  `total_amount` decimal(10,2) DEFAULT NULL,
  `discount` decimal(10,2) DEFAULT NULL,
  `final_amount` decimal(10,2) DEFAULT NULL,
  `order_status` varchar(20) DEFAULT 'Pending',
  `order_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `payment_id` varchar(100) DEFAULT NULL,
  `cook_id` int DEFAULT NULL,
  `waiter_id` int DEFAULT NULL,
  PRIMARY KEY (`order_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `visitor_orders`
--

LOCK TABLES `visitor_orders` WRITE;
/*!40000 ALTER TABLE `visitor_orders` DISABLE KEYS */;
INSERT INTO `visitor_orders` VALUES (1,'om ingole','ingoleom38@gmail.com','9307170583','10',420.00,0.00,420.00,'Cooking','2026-04-16 13:08:40',NULL,4,3),(2,'om ingole','ingoleom38@gmail.com','9307170583','10',450.00,0.00,450.00,'Pending','2026-04-16 14:34:35',NULL,NULL,NULL);
/*!40000 ALTER TABLE `visitor_orders` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-16 15:41:59
