import logging

from smartmeter.reader_data import ReaderDataPoint
from .data_sink import DataSink


class LoggerSink(DataSink):
    def __init__(self, logger_name: str) -> None:
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(logging.INFO)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, data_point: ReaderDataPoint) -> None:
        self._logger.info(str(data_point))