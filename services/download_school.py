import os
import requests

DOWNLOAD_FOLDER = "data/imports"


def download_file(url, filename):

    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    file_path = os.path.join(DOWNLOAD_FOLDER, filename)

    print("다운로드 시작...")

    response = requests.get(url, timeout=120)

    response.raise_for_status()

    with open(file_path, "wb") as f:
        f.write(response.content)

    print("다운로드 완료")

    return file_path