DROP TABLE IF EXISTS `pubnodes_wrkz`;
CREATE TABLE `pubnodes_wrkz` (
  `name` varchar(128) NOT NULL,
  `url` varchar(128) CHARACTER SET ascii NOT NULL,
  `port` int(11) NOT NULL,
  `url_port` varchar(128) CHARACTER SET ascii NOT NULL,
  `ssl` tinyint(4) NOT NULL DEFAULT 0,
  `cache` tinyint(4) NOT NULL DEFAULT 0,
  `fee_address` varchar(128) CHARACTER SET ascii DEFAULT NULL,
  `fee_fee` int(11) DEFAULT NULL,
  `online` tinyint(4) NOT NULL DEFAULT 1,
  `version` varchar(16) CHARACTER SET ascii NOT NULL,
  `timestamp` int(11) NOT NULL,
  `getinfo_dump` varchar(1024) DEFAULT NULL,
  KEY `url_port` (`url_port`),
  KEY `timestamp` (`timestamp`),
  KEY `online` (`online`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 `PAGE_COMPRESSED`=1;
