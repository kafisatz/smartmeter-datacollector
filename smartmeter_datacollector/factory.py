#
# Copyright (C) 2022 Supercomputing Systems AG
# This file is part of smartmeter-datacollector.
#
# SPDX-License-Identifier: GPL-2.0-only
# See LICENSES/README.md for more information.
#
import os 
import logging
from configparser import ConfigParser
from typing import List

from .collector import Collector
from .config import InvalidConfigError
from .sinks.data_sink import DataSink
from .sinks.logger_sink import LoggerSink
from .sinks.mqtt_sink import MqttConfig, MqttDataSink
from .sinks.influxdb_sink import InfluxdbDataSink, InfluxdbConfig
from .smartmeter.iskraam550 import IskraAM550
from .smartmeter.lge450 import LGE450
from .smartmeter.meter import Meter, MeterError

LOGGER = logging.getLogger("sink")
INFLUXDB_CONFIG_FILE = "/home/pi/.influxdb_config"

def build_meters(config: ConfigParser) -> List[Meter]:
    meters = []
    for section_name in filter(lambda sec: sec.startswith("reader"), config.sections()):
        meter_config = config[section_name]
        meter_type = meter_config.get('type')
        try:
            if meter_type == "lge450":
                meters.append(LGE450(
                    port=meter_config.get('port', "/dev/ttyUSB0"),
                    baudrate=meter_config.getint('baudrate', 2400),
                    decryption_key=meter_config.get('key')
                ))
            elif meter_type == "iskraam550":
                meters.append(IskraAM550(
                    port=meter_config.get('port', "/dev/ttyUSB0"),
                    baudrate=meter_config.getint('baudrate', 115200),
                    decryption_key=meter_config.get('key')
                ))
            else:
                raise InvalidConfigError(f"'type' is invalid or missing: {meter_type}")
        except MeterError as ex:
            logging.warning("%s Skipping smart meter.", ex)
            continue
    return meters


def build_sinks(config: ConfigParser) -> List[DataSink]:
    sinks = []
    for section_name in filter(lambda sec: sec.startswith("sink"), config.sections()):
        sink_config = config[section_name]
        sink_type = sink_config.get('type')
                
        if sink_type == "logger":
            sinks.append(LoggerSink(
                logger_name=sink_config.get('name', "DataLogger")
            ))
        elif sink_type == "mqtt":
            mqtt_config = MqttConfig.from_sink_config(sink_config)
            sinks.append(MqttDataSink(mqtt_config))
        else:
            raise InvalidConfigError(f"'type' is invalid or missing: {sink_type}")
    
    ##add influxdb sink
    if os.path.isfile(INFLUXDB_CONFIG_FILE):
        LOGGER.info('Adding influxdb sink...')
        sink_type = "influxdb"
        influxdb_config = InfluxdbConfig.from_file_config(INFLUXDB_CONFIG_FILE)
        sinks.append(InfluxdbDataSink(influxdb_config))
        
    return sinks


def build_collector(readers: List[Meter], sinks: List[DataSink]) -> Collector:
    collector = Collector()

    for sink in sinks:
        collector.register_sink(sink)
    for reader in readers:
        reader.register(collector)
    return collector
