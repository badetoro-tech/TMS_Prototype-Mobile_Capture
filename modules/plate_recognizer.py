import requests
import json
from modules.image_edit import EditImage
import shutil

PLATERECOGNIZER_JSON_DUMP = False


class PlateRecognizer:

    def __init__(self, file_name, image_to_process):
        self.file_name = file_name
        self.image_to_process = image_to_process

    def process_plate(self, regions, token):
        with open(self.image_to_process, 'rb') as fp:
            response = requests.post(
                'https://api.platerecognizer.com/v1/plate-reader/',
                data=dict(regions=regions),  # Optional
                files=dict(upload=fp),
                headers={'Authorization': token})
            response.raise_for_status()

        # pprint(response.json())

        if PLATERECOGNIZER_JSON_DUMP:
            with open('extract.txt', 'a', encoding='utf-8') as data:
                json.dump(response.json(), data, ensure_ascii=False, indent=4)
                data.write('\n')

        plate_data = response.json()

        return plate_data

    def check_process_plate(self, regions, token):
        plate_data = self.process_plate(regions, token)

        if not plate_data['results']:
            edit_image = EditImage(self.file_name)
            edit_image.crop_image()
            self.process_plate(regions, token)

        return plate_data
