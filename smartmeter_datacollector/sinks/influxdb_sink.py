#
# Copyright (C) 2022 Supercomputing Systems AG
# This file is part of smartmeter-datacollector.
#
# SPDX-License-Identifier: GPL-2.0-only
# See LICENSES/README.md for more information.
#
import math
import json
import logging
import os
#import sys
#import ssl
from configparser import SectionProxy
from dataclasses import dataclass
from typing import Optional

from influxdb_client.client.exceptions import InfluxDBError
from datetime import datetime 
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WriteOptions

import asyncio
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

#async def main():
#    async with InfluxDBClientAsync(url="http://localhost:8086", token="my-token", org="my-org") as client:
#        ready = await client.ping()
#        print(f"InfluxDB: {ready}")


#from asyncio_mqtt import Client
#from asyncio_mqtt.client import ProtocolVersion
#from asyncio_mqtt.error import MqttCodeError, MqttError
#from paho.mqtt.client import MQTT_ERR_NO_CONN

from ..smartmeter.meter_data import MeterDataPoint
from .data_sink import DataSink

INFLUXDB_CONFIG_FILE = "/home/pi/.influxdb_config"
INFLUXDB_STROMZAEHLER_BUCKET = "strom"

LOGGER = logging.getLogger("sink")

def getIntegerPlaces(theNumber):
    if theNumber == 0:
        return 1
    else:
        if theNumber <= 999999999999997:
            return int(math.log10(abs(theNumber))) + 1
        else:
            return len(str(theNumber))
        
#influxdb_config = read_influxdb_config(INFLUXDB_CONFIG_FILE)
#for influxdb
def read_influxdb_config(fi):
    influxdb_config = {}
    
    with open(fi) as f:
        lines = f.readlines()
        
    LOGGER.debug(len(lines))
        
    for line in lines:
        line = line.replace('\n', '')
        line = line.replace('\r', '')
        if not line or line.startswith('#'):
            continue
        key, value = line.replace('export ', '', 1).strip().split('=', 1)
        print("key=")
        print(key)        
        #os.putenv(key,value)
        influxdb_config[key] = value
    
    return influxdb_config

@dataclass
class InfluxdbConfig:
    token: str
    org: str 
    host: str = 'localhost'
    user: Optional[str] = None
    password: Optional[str] = None

    def with_user_pass_auth(self, user: str, password: str) -> "InfluxdbConfig":
        self.user = user
        self.password = password
        return self
    
    @staticmethod
    def from_file_config(config: SectionProxy) -> "InfluxdbConfig":
        influxdb_config = read_influxdb_config(INFLUXDB_CONFIG_FILE)
        influxdb_cfg = InfluxdbConfig(influxdb_config.get("INFLUXDB_TOKEN"), influxdb_config.get("INFLUXDB_ORG"), influxdb_config.get("INFLUXDB_HOST"))
        if influxdb_config.get("INFLUXDB_USER") and influxdb_config.get("INFLUXDB_PASSWORD"):
            influxdb_cfg.with_user_pass_auth(
                influxdb_config.get("INFLUXDB_USER"),
                influxdb_config.get("INFLUXDB_PASSWORD"))       
        return influxdb_cfg

class InfluxdbDataSink(DataSink):
    TIMEOUT = 3
    influxdb_config = read_influxdb_config(INFLUXDB_CONFIG_FILE)
    INFLUXDB_ORG = influxdb_config.get("INFLUXDB_ORG")
    INFLUXDB_TOKEN = influxdb_config.get("INFLUXDB_TOKEN")
    INFLUXDB_HOST = influxdb_config.get("INFLUXDB_HOST")
    INFLUXDB_STROMZAEHLER_BUCKET = "strom"
    INFLUXDB_URL = "http://" + INFLUXDB_HOST
    
    def __init__(self, config: InfluxdbConfig) -> None:
        INFLUXDB_URL = config.host
        if not INFLUXDB_URL.startswith('http'):
            INFLUXDB_URL = "http://" + config.host
        self.client = InfluxDBClient(url=INFLUXDB_URL,org=config.org,token=config.token)
        #self.client = InfluxDBClient(url=INFLUXDB_URL,org=config.org,token=config.token)

    async def start(self) -> None:        
        if await self._connect_to_server():
            LOGGER.info("Connected to Influxdb.")

    async def stop(self) -> None:
        await self._disconnect_from_server()
        LOGGER.info("Disconnected from Influxdb.")

    async def send(self, data_point: MeterDataPoint) -> None:
        #LOGGER.info("topic")
        #LOGGER.info(topic)
        #LOGGER.info("dp_json")
        #LOGGER.info(dp_json)
        
        record_type = data_point.type.identifier
        src = data_point.source
        val = int(data_point.value)
        val_len = getIntegerPlaces(val)
        n_spaces = 20 - val_len
        ts = int(data_point.timestamp.timestamp())
        dt = datetime.fromtimestamp(ts)
        
        log_msg = "data was sent to Influxdb dt = " + str(dt) + " value = " + str(val) + n_spaces*" " + " record_type = " + record_type
        
        #LOGGER.info("val")
        #LOGGER.info(val)
        #LOGGER.info("ts")
        #LOGGER.info(ts)
        #LOGGER.info("dt")
        #LOGGER.info(dt)        
        #LOGGER.info(record_type)
        #LOGGER.info(src)
        #LOGGER.info(val)
        #LOGGER.info(dt)
        
        ###############################################################
        #non async version:
        #WORKS!
        ###############################################################
        
        try:
            if False: 
                write_api = self.client.write_api()
                write_api.write(self.INFLUXDB_STROMZAEHLER_BUCKET, self.INFLUXDB_ORG,Point("stromzaehler").tag("zaehlernummer",src).tag("type", record_type).field("value", val).time(time = dt))
                LOGGER.info(log_msg)
                
        ###############################################################
        ###############################################################

        ###############################################################
        #async version
        ###############################################################
            if True:
                async with InfluxDBClientAsync(url=self.INFLUXDB_URL, token=self.INFLUXDB_TOKEN, org=self.INFLUXDB_ORG) as client:
                    write_api = client.write_api()
                    successfully = await write_api.write(self.INFLUXDB_STROMZAEHLER_BUCKET, self.INFLUXDB_ORG,Point("stromzaehler").tag("zaehlernummer",src).tag("type", record_type).field("value", val).time(time = dt))                    
                    LOGGER.info(log_msg)
                    LOGGER.debug(f" > successfully: {successfully}")
                    
###############################################################
###############################################################                    
        except ValueError as ex:
            LOGGER.error("Influxdb payload or topic is invalid: '%s'", ex)
        except InfluxDBError as ex:
            if ex.response.status == 401:
                LOGGER.error(f"Insufficient write permissions to bucket", ex)
        except Exception as ex:
            LOGGER.error(f"Influxdb error", ex)

    async def _connect_to_server(self) -> bool:
        try:
            results = self.client.buckets_api().find_buckets()
            #print(results)
            #print(type(results)) #<class 'influxdb_client.domain.buckets.Buckets'>
            #LOGGER.info("InfluxDB - Length of buckets result: ",len(results.to_str())) #should be larger 0
            LOGGER.info("InfluxDB - Connected to InfluxDB.")            
        except Exception as ex:
            LOGGER.error(ex)
            return False
        return True

    async def _disconnect_from_server(self) -> None:
        try:
            #await self._client.disconnect(timeout=self.TIMEOUT)
            await self.client.close()
        except Exception as ex:
            LOGGER.error(ex)
            #await self._client.force_disconnect()

    @staticmethod
    def get_topic_name_for_datapoint(data_point: MeterDataPoint) -> str:
        return f"smartmeter/{data_point.source}/{data_point.type.identifier}"

    @staticmethod
    def data_point_to_influxdb_json(data_point: MeterDataPoint) -> str:
        return json.dumps({
            #BK: all data seems to be parsed from Int32 or similar -> send data as integer to MQTT
            "value": int(data_point.value),
            "timestamp": int(data_point.timestamp.timestamp())
        })


