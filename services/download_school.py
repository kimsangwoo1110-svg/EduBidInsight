"""Backward-compatible entry point for the NEIS school connector."""

from services.connectors.neis_school import NeisSchoolConnector


def _api_error_message(data):
    return NeisSchoolConnector.api_error_message(data)


def _extract_school_info(data):
    return NeisSchoolConnector.extract_school_info(data)


def download_school_data(progress_callback=None):
    """Synchronize NEIS schools and return the legacy processed-school count."""

    def report(progress):
        if progress_callback is None:
            return
        compatible_progress = dict(progress)
        if "downloaded" not in compatible_progress and "processed" in progress:
            compatible_progress["downloaded"] = progress["processed"]
        progress_callback(compatible_progress)

    result = NeisSchoolConnector().synchronize(report)
    return result["inserted"] + result["updated"]
