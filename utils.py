from pathlib import Path
from tensorflow.keras.preprocessing.image import load_img
import shutil
import os
from PIL import Image
import pandas as pd
import numpy as np
from datetime import datetime

OPT_PERMS = [
    ['R', 'wA', 'wB'],
    ['R', 'wB', 'wA'],
    ['wA', 'R', 'wB'],
    ['R', 'wA', 'wB'],
    ['wA', 'R', 'wB'],
    ['R', 'wB', 'wA'],
    ['R', 'wA', 'wB'],
    ['wB', 'wA', 'R'],
    ['R', 'wA', 'wB'],
    ['wA', 'R', 'wB'],
    ['R', 'wA', 'wB'],
    ['wB', 'wA', 'R'],
    ['wA', 'R', 'wB'],
    ['R', 'wA', 'wB'],
    ['wA', 'R', 'wB'],
    ['R', 'wA', 'wB'],
    ['wA', 'wB', 'R'],
    ['wB', 'wA', 'R'],
    ['R', 'wA', 'wB'],
    ['wB', 'wA', 'R'],
    ['R', 'wB', 'wA'],
    ['R', 'wA', 'wB'],
    ['wA', 'R', 'wB'],
    ['R', 'wA', 'wB'],
    ['wB', 'R', 'wA'],
    ['wB', 'wA', 'R'],
    ['R', 'wA', 'wB'],
    ['wA', 'R', 'wB']
]

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

def make_question_folders_from_root():
    path = Path('./questions')
    original_permutation = pd.read_csv('./questions/permutations/original_permutation.csv',
                                       header=None, index_col=None).values

    filesafe_datetime = datetime.now().strftime('%Y_%M_%d_%H_%M_%S')
    live_dir = f'{str(path)}/live'
    q_type_counts = {'mehe': 0, 'mehh': 0, 'mhhe': 0, 'mhhh': 0}
    perm_header = ('q_num', 'q_id', 'q_type', 'sample_id', 'created')
    perm_df = pd.DataFrame(columns=perm_header)
    for q_num in range(1, 29):
        q_type = original_permutation[q_num-1][2]
        sample_id = original_permutation[q_num-1][1]
        q_type_id = q_type_counts[q_type]
        q_type_counts[q_type] += 1
        q_id = f'{q_type}_{q_type_id}'
        q_dir = f'{live_dir}/{q_id}'
        if not os.path.exists(q_dir):
            os.makedirs(q_dir)
        perm_df.loc[q_num-1] = (q_num, q_id, q_type, sample_id, filesafe_datetime)
        for q_file in path.glob(f'Q{q_num}_*'):
            q_filename = q_file.parts[-1]
            q_filename = q_filename[q_filename.index('_')+1:]
            file_id = f'{q_id}_{q_filename}'
            shutil.copy(q_file, f'{q_dir}/{file_id}')
            open(f'{q_dir}/sampleID-{sample_id}', 'a').close()

    perm_dir = f'{str(path)}/permutations/perm_0'
    if not os.path.exists(perm_dir):
        os.makedirs(perm_dir)
    perm_df.to_csv(f'{perm_dir}/permutation.csv', index_label='Index')
    print('test')
    # perm_qs_dir = f'{perm_dir}/questions'

def create_permutation():
    filesafe_datetime = datetime.now().strftime('%Y_%M_%d_%H_%M_%S')
    block_a = ['mehh'] * 6 + ['mhhh'] * 2 + ['mehe'] * 3 + ['mhhe'] * 1
    block_b = ['mehh'] * 6 + ['mhhh'] * 2 + ['mehe'] * 3 + ['mhhe'] * 1
    adv_block = ['mhhe', 'mehh', 'mehh', 'mhhe']

    perm_a = np.random.permutation(len(block_a))
    perm_b = np.random.permutation(len(block_b))
    order_a = [block_a[i] for i in perm_a]
    order_b = [block_b[i] for i in perm_b]
    new_order = order_a + adv_block + order_b

    print('test')

    perm_ids = [p.parts[-1][p.parts[-1].index('_')+1:] for p in list(Path('./questions/permutations').glob('perm_*'))]
    new_perm_id = int(max(sorted(perm_ids, key=lambda x: int(x)))) + 1

    perm_dir = f'./questions/permutations/perm_{new_perm_id}'
    if not os.path.exists(perm_dir):
        os.makedirs(f'{perm_dir}/questions')

    mehes = [p for p in list(Path('./questions/live').glob('*')) if 'mehe' in p.parts[-1]]
    mehhs = [p for p in list(Path('./questions/live').glob('*')) if 'mehh' in p.parts[-1]]
    mhhes = [p for p in list(Path('./questions/live').glob('*')) if 'mhhe' in p.parts[-1]]
    mhhhs = [p for p in list(Path('./questions/live').glob('*')) if 'mhhh' in p.parts[-1]]

    np.random.shuffle(mehes)
    np.random.shuffle(mehhs)
    np.random.shuffle(mhhes)
    np.random.shuffle(mhhhs)

    q_type_counts = {'mehe': 0, 'mehh': 0, 'mhhe': 0, 'mhhh': 0}
    perm_header = ('q_num', 'q_id', 'q_type', 'sample_id', 'created')
    perm_df = pd.DataFrame(columns=perm_header)

    q_num = 1
    for q_type in new_order:
        if q_type == 'mehe':
            q_source_dir = mehes[0]
            mehes.remove(q_source_dir)
        elif q_type == 'mehh':
            q_source_dir = mehhs[0]
            mehhs.remove(q_source_dir)
        elif q_type == 'mhhe':
            q_source_dir = mhhes[0]
            mhhes.remove(q_source_dir)
        else:
            assert q_type == 'mhhh'
            q_source_dir = mhhhs[0]
            mhhhs.remove(q_source_dir)

        q_id = q_source_dir.parts[-1]
        sidfile = list(q_source_dir.glob('sampleID*'))[0].parts[-1]
        sample_id = sidfile[sidfile.index('-')+1:]
        perm_df.loc[q_num-1] = (q_num, q_id, q_type, sample_id, filesafe_datetime)

        q_files = list(q_source_dir.glob(f'{q_id}*'))
        for q_file in q_files:
            fname = q_file.parts[-1]
            new_fname = f'Q{q_num}{fname[fname.index(q_id)+len(q_id):]}'
            new_dest = f'{perm_dir}/questions/{new_fname}'
            shutil.copy(q_file, new_dest)
        q_num += 1

    perm_df.to_csv(f'{perm_dir}/permutation.csv', index_label='Index')


def make_permutation_live(perm_path):
    questions_path = Path(perm_path + '/questions')
    print('test')
    for q_file in questions_path.glob('*'):
        q_name = q_file.parts[-1]
        q_dest = f'./questions/{q_name}'
        print('test')
        shutil.copy(q_file, q_dest)




if __name__ == '__main__':
    pass
    # png_to_jpg('questions/eg_barchart.png')
    # png_to_jpg('questions/eg_exp_1.png')
    # png_to_jpg('questions/eg_exp_2.png')
    # png_to_jpg('questions/eg_exp_3.png')
    # for i in range(1, 29):
        # thumbnail_image(f'questions/Q{i}_sample.jpg')
        # thumbnail_image(f'questions/Q{i}_exp_correct.jpg')
        # thumbnail_image(f'questions/Q{i}_exp_wrong_A.jpg')
        # thumbnail_image(f'questions/Q{i}_exp_wrong_B.jpg')
    # thumbnail_image(f'questions/ADV13_exp_correct.jpg')
    # thumbnail_image(f'questions/ADV13_exp_wrong_A.jpg')
    # thumbnail_image(f'questions/ADV13_exp_wrong_B.jpg')
    # thumbnail_image(f'questions/ADV16_exp_correct.jpg')
    # thumbnail_image(f'questions/ADV16_exp_wrong_A.jpg')
    # thumbnail_image(f'questions/ADV16_exp_wrong_B.jpg')
    # thumbnail_image(f'questions/eg_exp_1.jpg')
    # thumbnail_image(f'questions/eg_exp_2.jpg')
    # thumbnail_image(f'questions/eg_exp_3.jpg')
    # thumbnail_image(f'questions/eg_sample.jpg')

    # make_question_folders_from_root()

    # create_permutation()

    make_permutation_live('./questions/permutations/perm_5')




