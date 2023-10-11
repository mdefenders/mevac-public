from zoneinfo import ZoneInfo
from datetime import datetime


class Utils:
    @staticmethod
    def mastodon_timestamp_to_epoch(date_string):
        # Fixing Zulu
        datetime_obj = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
        datetime_obj = datetime_obj.replace(tzinfo=ZoneInfo('UTC'))
        return int(datetime_obj.timestamp())
