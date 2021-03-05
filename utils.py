from pathlib import Path
from tensorflow.keras.preprocessing.image import load_img
import shutil
import os
from PIL import Image

def png_to_jpg(path, archive_old=True, archive_dir='archive'):
    path = Path(path)
    img = load_img(path)
    jpg_name = path.parts[-1][:path.parts[-1].index('.png')] + '.jpg'
    img.save(f'{str(path.parent)}/{jpg_name}')
    if archive_old:
        archive_path = Path(f'{str(path.parent)}/{archive_dir}')
        if not os.path.exists(archive_path):
            os.makedirs(archive_path)
        shutil.move(path, f'{str(archive_path)}/{path.parts[-1]}')

def thumbnail_image(path, max_size=(300, 300), archive_old=True, archive_dir='archive'):
    path = Path(path)
    if archive_old:
        archive_path = Path(f'{str(path.parent)}/{archive_dir}')
        if not os.path.exists(archive_path):
            os.makedirs(archive_path)
        shutil.copy(path, f'{str(archive_path)}/{path.parts[-1]}')
    img = load_img(path)
    img.thumbnail(max_size, Image.ANTIALIAS)
    img.save(path)



if __name__ == '__main__':
    # png_to_jpg('questions/eg_barchart.png')
    # png_to_jpg('questions/eg_exp_1.png')
    # png_to_jpg('questions/eg_exp_2.png')
    # png_to_jpg('questions/eg_exp_3.png')
    for i in range(1, 29):
        # thumbnail_image(f'questions/Q{i}_sample.jpg')
        thumbnail_image(f'questions/Q{i}_exp_correct.jpg')
        thumbnail_image(f'questions/Q{i}_exp_wrong_A.jpg')
        thumbnail_image(f'questions/Q{i}_exp_wrong_B.jpg')

