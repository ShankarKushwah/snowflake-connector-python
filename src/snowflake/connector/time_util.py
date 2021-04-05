#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2021 Snowflake Computing Inc. All right reserved.
#

import random
import time
from logging import getLogger
from typing import Optional

logger = getLogger(__name__)

try:
    from threading import _Timer as Timer
except ImportError:
    from threading import Timer

DEFAULT_MASTER_VALIDITY_IN_SECONDS = 4 * 60 * 60  # seconds


class HeartBeatTimer(Timer):
    """A thread which executes a function every client_session_keep_alive_heartbeat_frequency seconds."""

    def __init__(self, client_session_keep_alive_heartbeat_frequency, f):
        interval = client_session_keep_alive_heartbeat_frequency
        super(HeartBeatTimer, self).__init__(interval, f)

    def run(self):
        while not self.finished.is_set():
            self.finished.wait(self.interval)
            if not self.finished.is_set():
                try:
                    self.function()
                except Exception as e:
                    logger.debug("failed to heartbeat: %s", e)


def get_time_millis() -> int:
    """Returns the current time in milliseconds."""
    return int(time.time() * 1000)


class DecorrelateJitterBackoff(object):
    # Decorrelate Jitter backoff
    # https://www.awsarchitectureblog.com/2015/03/backoff.html
    def __init__(self, base, cap):
        self._base = base
        self._cap = cap

    def next_sleep(self, _, sleep):
        return min(self._cap, random.randint(self._base, sleep * 3))


class TimeCNM:
    """Context manager class to easily measure execution of a code block.

    Once the context manager finishes, the class should be cast into an int to retrieve
    result.

    Example:

        with TimeCNM() as measured_time:
            pass
        download_metric = int(measured_time)
    """

    def __init__(self):
        self._start: Optional[int] = None
        self._end: Optional[int] = None

    def __enter__(self) -> "TimeCNM":
        self._start = get_time_millis()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._end = get_time_millis()

    def __int__(self) -> int:
        if self._start is None or self._end is None:
            raise Exception("Trying to get timing before TimeCNM has finished")
        return self._end - self._start
