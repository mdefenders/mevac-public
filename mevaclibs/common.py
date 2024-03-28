from zoneinfo import ZoneInfo
from datetime import datetime


class Utils:
    @staticmethod
    def mastodon_timestamp_to_epoch(date_string):
        return Utils.fix_date(datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ"))

    @staticmethod
    def as_timestamp_to_epoch(date_string):
        return Utils.fix_date(datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ"))

    @staticmethod
    def fix_date(datetime_obj):
        # Fixing Zulu
        datetime_obj = datetime_obj.replace(tzinfo=ZoneInfo('UTC'))
        return int(datetime_obj.timestamp())

