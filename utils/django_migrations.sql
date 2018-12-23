-- MySQL dump 10.13  Distrib 5.7.17, for osx10.12 (x86_64)
--
-- Host: 127.0.0.1    Database: jumpserver
-- ------------------------------------------------------
-- Server version	5.7.19

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `django_migrations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=99 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2018-10-16 03:54:01.083767'),(2,'contenttypes','0002_remove_content_type_name','2018-10-16 03:54:01.134230'),(3,'auth','0001_initial','2018-10-16 03:54:01.303742'),(4,'auth','0002_alter_permission_name_max_length','2018-10-16 03:54:01.336313'),(5,'auth','0003_alter_user_email_max_length','2018-10-16 03:54:01.348483'),(6,'auth','0004_alter_user_username_opts','2018-10-16 03:54:01.360740'),(7,'auth','0005_alter_user_last_login_null','2018-10-16 03:54:01.371895'),(8,'auth','0006_require_contenttypes_0002','2018-10-16 03:54:01.378513'),(9,'auth','0007_alter_validators_add_error_messages','2018-10-16 03:54:01.388758'),(10,'auth','0008_alter_user_username_max_length','2018-10-16 03:54:01.400890'),(11,'users','0001_initial','2018-10-16 03:54:01.944343'),(12,'admin','0001_initial','2018-10-16 03:54:02.034975'),(13,'admin','0002_logentry_remove_auto_add','2018-10-16 03:54:02.049349'),(14,'admin','0003_logentry_add_action_flag_choices','2018-10-16 03:54:02.064696'),(15,'assets','0001_initial','2018-10-16 03:54:02.667713'),(16,'assets','0002_auto_20180105_1807','2018-10-16 03:54:02.705499'),(17,'assets','0003_auto_20180109_2331','2018-10-16 03:54:02.813949'),(18,'assets','0004_auto_20180125_1218','2018-10-16 03:54:02.877967'),(19,'assets','0005_auto_20180126_1637','2018-10-16 03:54:03.011673'),(20,'assets','0006_auto_20180130_1502','2018-10-16 03:54:03.265462'),(21,'assets','0007_auto_20180225_1815','2018-10-16 03:54:03.613870'),(22,'assets','0008_auto_20180306_1804','2018-10-16 03:54:03.821335'),(23,'assets','0009_auto_20180307_1212','2018-10-16 03:54:03.843992'),(24,'assets','0010_auto_20180307_1749','2018-10-16 03:54:03.871740'),(25,'assets','0011_auto_20180326_0957','2018-10-16 03:54:04.041219'),(26,'assets','0012_auto_20180404_1302','2018-10-16 03:54:04.100811'),(27,'assets','0013_auto_20180411_1135','2018-10-16 03:54:04.218430'),(28,'assets','0014_auto_20180427_1245','2018-10-16 03:54:04.328114'),(29,'assets','0015_auto_20180510_1235','2018-10-16 03:54:04.355353'),(30,'assets','0016_auto_20180511_1203','2018-10-16 03:54:04.382377'),(31,'assets','0017_auto_20180702_1415','2018-10-16 03:54:04.542299'),(32,'assets','0018_auto_20180807_1116','2018-10-16 03:54:04.928882'),(33,'assets','0019_auto_20180816_1320','2018-10-16 03:54:04.996638'),(34,'assets','0020_auto_20180816_1652','2018-10-16 03:54:05.343654'),(35,'assets','0021_auto_20180903_1132','2018-10-16 03:54:05.370216'),(36,'assets','0022_auto_20181012_1717','2018-10-16 03:54:05.538709'),(37,'users','0002_auto_20171225_1157','2018-10-16 03:54:05.698481'),(38,'users','0003_auto_20180101_0046','2018-10-16 03:54:05.711697'),(39,'users','0004_auto_20180125_1218','2018-10-16 03:54:05.772696'),(40,'users','0005_auto_20180306_1804','2018-10-16 03:54:05.797780'),(41,'users','0006_auto_20180411_1135','2018-10-16 03:54:05.948125'),(42,'users','0007_auto_20180419_1036','2018-10-16 03:54:06.091956'),(43,'users','0008_auto_20180425_1516','2018-10-16 03:54:06.105389'),(44,'users','0009_auto_20180517_1537','2018-10-16 03:54:06.131188'),(45,'users','0010_auto_20180606_1505','2018-10-16 03:54:06.321848'),(46,'users','0011_user_source','2018-10-16 03:54:06.428777'),(47,'users','0012_auto_20180710_1641','2018-10-16 03:54:06.514067'),(48,'users','0013_auto_20180807_1116','2018-10-16 03:54:06.650543'),(49,'users','0014_auto_20180816_1652','2018-10-16 03:54:06.746302'),(50,'audits','0001_initial','2018-10-16 03:54:06.779067'),(51,'audits','0002_ftplog_org_id','2018-10-16 03:54:06.816801'),(52,'audits','0003_auto_20180816_1652','2018-10-16 03:54:06.855191'),(53,'audits','0004_operatelog_passwordchangelog_userloginlog','2018-10-16 03:54:06.907298'),(54,'auth','0009_alter_user_last_name_max_length','2018-10-16 03:54:06.922438'),(55,'captcha','0001_initial','2018-10-16 03:54:06.952390'),(56,'common','0001_initial','2018-10-16 03:54:06.979536'),(57,'common','0002_auto_20180111_1407','2018-10-16 03:54:07.040816'),(58,'common','0003_setting_category','2018-10-16 03:54:07.072335'),(59,'common','0004_setting_encrypted','2018-10-16 03:54:07.108007'),(60,'django_celery_beat','0001_initial','2018-10-16 03:54:07.246440'),(61,'django_celery_beat','0002_auto_20161118_0346','2018-10-16 03:54:07.330192'),(62,'django_celery_beat','0003_auto_20161209_0049','2018-10-16 03:54:07.356330'),(63,'django_celery_beat','0004_auto_20170221_0000','2018-10-16 03:54:07.365220'),(64,'django_celery_beat','0005_add_solarschedule_events_choices','2018-10-16 03:54:07.377127'),(65,'django_celery_beat','0006_auto_20180210_1226','2018-10-16 03:54:07.414056'),(66,'ops','0001_initial','2018-10-16 03:54:07.627395'),(67,'ops','0002_celerytask','2018-10-16 03:54:07.653158'),(68,'orgs','0001_initial','2018-10-16 03:54:07.849837'),(69,'orgs','0002_auto_20180903_1132','2018-10-16 03:54:07.865926'),(70,'perms','0001_initial','2018-10-16 03:54:08.126412'),(71,'perms','0002_auto_20171228_0025','2018-10-16 03:54:08.328918'),(72,'perms','0003_auto_20180225_1815','2018-10-16 03:54:08.501763'),(73,'perms','0004_auto_20180411_1135','2018-10-16 03:54:08.770485'),(74,'perms','0005_migrate_data_20180411_1144','2018-10-16 03:54:08.871984'),(75,'perms','0006_auto_20180606_1505','2018-10-16 03:54:08.947327'),(76,'perms','0007_auto_20180807_1116','2018-10-16 03:54:09.158080'),(77,'perms','0008_auto_20180816_1652','2018-10-16 03:54:09.277244'),(78,'perms','0009_auto_20180903_1132','2018-10-16 03:54:09.312652'),(79,'sessions','0001_initial','2018-10-16 03:54:09.347562'),(80,'terminal','0001_initial','2018-10-16 03:54:09.588109'),(81,'terminal','0002_auto_20171228_0025','2018-10-16 03:54:09.864943'),(82,'terminal','0003_auto_20171230_0308','2018-10-16 03:54:09.916736'),(83,'terminal','0004_session_remote_addr','2018-10-16 03:54:09.955561'),(84,'terminal','0005_auto_20180122_1154','2018-10-16 03:54:10.032369'),(85,'terminal','0006_auto_20180123_1037','2018-10-16 03:54:10.053268'),(86,'terminal','0007_session_date_last_active','2018-10-16 03:54:10.093694'),(87,'terminal','0008_auto_20180307_1603','2018-10-16 03:54:10.124400'),(88,'terminal','0009_auto_20180326_0957','2018-10-16 03:54:10.233769'),(89,'terminal','0010_auto_20180423_1140','2018-10-16 03:54:10.380928'),(90,'terminal','0011_auto_20180807_1116','2018-10-16 03:54:10.467649'),(91,'terminal','0012_auto_20180816_1652','2018-10-16 03:54:10.557186'),(92,'xpack','0001_initial','2018-10-16 03:54:11.066130'),(93,'assets','0023_auto_20181016_1603','2018-10-16 08:40:26.566475'),(94,'assets','0024_auto_20181016_1640','2018-10-16 08:40:26.654385'),(95,'assets','0025_auto_20181016_1640','2018-10-16 08:40:45.837227'),(96,'assets','0023_auto_20181016_1650','2018-10-16 08:50:48.274294'),(97,'users','0015_auto_20181105_1112','2018-11-09 03:58:37.965880'),(98,'users','0016_auto_20181109_1505','2018-11-13 03:42:19.711320');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2018-11-13 16:02:01
