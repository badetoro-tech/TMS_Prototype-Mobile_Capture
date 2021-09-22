from PIL import Image, ImageOps

IMG_DIR = 'static/vehicle-capture/uploads'
PROCESSED_DIR = 'static/vehicle-capture/processed'
ORIG_PROC_DIR = 'static/vehicle-capture/original'
WIP = 'static/vehicle-capture/WIP'
CROPPED = 'static/vehicle-capture/cropped'


class AllPaths:
    def __init__(self):
        self.upload_path = IMG_DIR
        self.wip_path = WIP
        self.processed_path = PROCESSED_DIR
        self.original_file_path = ORIG_PROC_DIR
        self.cropped_path = CROPPED


class EditImage:
    """Image Editing Class"""

    def __init__(self, file_name):
        self.file_name = file_name
        self.upload_path = IMG_DIR
        self.wip = WIP
        self.uploaded_file = f'{IMG_DIR}/{file_name}'
        self.processing_file = f'{WIP}/{file_name}'
        self.cropped_file = f'{CROPPED}/{file_name}'

    def crop_image(self):
        # Try image cropping
        img = Image.open(self.uploaded_file)
        exif = img.getexif()
        width, height = img.size

        # print(f'*** Image Width = {img.size[0]} | Image Height = {img.size[1]}')
        # Setting the points for cropped image
        left = round(width / 8)
        top = round(height / 8)
        right = round(width / 8) * 6
        bottom = round(height / 8) * 6

        # print(f 'left: {left} | top: {top} | right: {right} | bottom: {bottom}')

        # Cropped image of above dimension
        cropped_img = img.crop((left, top, right, bottom))
        cropped_img.save(self.cropped_file, exif=exif)

        self.resize_img(cropped_img)

    def resize_img(self, img, exif):
        base_height = 1024

        h_percent = (base_height / float(img.size[1]))
        w_size = int((float(img.size[0]) * float(h_percent)))
        img = img.resize((w_size, base_height), Image.ANTIALIAS)

        # print(f'Image Width = {img.size[0]} | Image Height = {img.size[1]}')

        img.save(self.processing_file, exif=exif)
