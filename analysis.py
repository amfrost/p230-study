import pickle
import os
import sys
import numpy as np
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
from monkey import get_survey_details
from pprint import pprint
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu, wilcoxon
from sentiments import SENTIMENTS

pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)
pd.set_option('display.width', 1000)

def analysis():
    survey_pulls_dir = Path('./monkey_data/survey_pulls')
    latest_id = max([int(p.parts[-1]) for p in list(survey_pulls_dir.glob('*'))])
    all_responses = pickle.load(open(f'{survey_pulls_dir}/{latest_id}/all_responses.pkl', 'rb'))

    original_permutation = pd.read_csv('./questions/permutations/original_permutation_upd.csv')
    survey_details = get_survey_details()
    survey_details = {k: json.loads(v.text) for k, v in survey_details.items()}

    livetimes = []
    permutations = {}
    for i in range(len(list(Path('./questions/permutations').glob('perm_*')))):
        livetime = Path(f'./questions/permutations/perm_{i}/livetimes.txt')
        livetime = open(livetime, 'r').read()
        livetime = datetime.strptime(livetime, '%d/%m/%Y %H%M')
        livetimes.append(livetime)
        perm_csv = pd.read_csv(f'./questions/permutations/perm_{i}/permutation.csv')
        merge = pd.merge(perm_csv, original_permutation, on='sample_id', how='left', suffixes=('_perm', '_orig'))
        permutations[i] = merge
    livetimes.append(datetime.now())

    valid_responses = []
    completed = 0
    for group, response in all_responses.items():
        data = json.loads(response.text)['data']
        for individual in data:
            grp_survey = survey_details[group]
            individual['valid'] = True
            if individual['response_status'] != 'completed':
                individual['valid'] = False
            else:
                completed += 1
            individual['group'] = group
            modified_dt = datetime.strptime(individual['date_modified'], '%Y-%m-%dT%H:%M:%S+00:00')
            created_dt = datetime.strptime(individual['date_created'], '%Y-%m-%dT%H:%M:%S+00:00')
            individual['date_modified'] = modified_dt
            individual['date_created'] = created_dt
            perm_num = -1
            for i in range(len(livetimes)):
                if created_dt >= livetimes[i] and modified_dt < livetimes[i + 1]:
                    perm_num = i
                    break
            individual['permutation'] = perm_num
            if perm_num == -1:
                individual['valid'] = False

            if individual['valid']:
                permutation = permutations[perm_num]
                # valid_responses.append(individual)
                individual['part-a_answers'] = []
                individual['part-b_answers'] = []
                individual['part-a_cls_confs'] = []
                individual['part-b_cls_confs'] = []
                individual['changed_answer'] = []
                individual['changed_to_classifier'] = []
                individual['agreed_with_classifier'] = []
                individual['reinforced_by_classifier'] = []
                for q_num in range(28):
                    choice_a = individual['pages'][q_num*2 + 1]['questions'][0]['answers'][0]['choice_id']
                    choice_b = individual['pages'][q_num*2 + 2]['questions'][0]['answers'][0]['choice_id']
                    part_a_opts = grp_survey['pages'][q_num*2 + 1]['questions'][0]['answers']['choices']
                    part_b_opts = grp_survey['pages'][q_num*2 + 2]['questions'][-1]['answers']['choices']
                    answer_a = 'A' if part_a_opts[0]['id'] == choice_a else 'B' if part_a_opts[1]['id'] == choice_a else 'C'
                    answer_b = 'A' if part_b_opts[0]['id'] == choice_b else 'B' if part_b_opts[1]['id'] == choice_b else 'C'
                    individual['part-a_answers'].append(answer_a)
                    individual['part-b_answers'].append(answer_b)
                    part_a_cls_conf = permutation.iloc[q_num][f'conf_{answer_a}']
                    part_b_cls_conf = permutation.iloc[q_num][f'conf_{answer_b}']
                    individual['part-a_cls_confs'].append(part_a_cls_conf)
                    individual['part-b_cls_confs'].append(part_b_cls_conf)
                    individual['changed_answer'].append(answer_a != answer_b)
                    if group in ['B', 'D'] and (q_num == 12 or q_num == 15):
                            top_cls_ans = 'C'
                    else:
                        top_cls_ans = ['A', 'B', 'C'][np.argmax(permutation.iloc[q_num][['conf_A', 'conf_B', 'conf_C']])]
                    individual['changed_to_classifier'].append(answer_a != answer_b and top_cls_ans == answer_b)
                    individual['agreed_with_classifier'].append(answer_b == top_cls_ans)
                    # individual['disagreed_with_classifier'].append(answer_b != top_cls_ans)
                    # print('test')
                if individual['pages'][-1]['questions']:
                    feedback = individual['pages'][-1]['questions'][0]['answers'][0]['text']
                    individual['feedback'] = feedback
                    individual['sentiments'] = SENTIMENTS[feedback]
                else:
                    individual['sentiments'] = False

                valid_responses.append(individual)

    stat = 'agreed_with_classifier'
    stat = 'changed_answer'
    stat = 'changed_to_classifier'
    alternative = 'two-sided'
    alternative = 'less'
    alternative = 'greater'

    summary_stats = {}
    ind_stats = {}
    for grp in ['A', 'B', 'C', 'D']:
        ind_stats[grp] = {'before_adv1': [], 'post_adv2': [], 'mehh_before_adv1': [], 'mehh_post_adv2': []}

        grp_responses = [resp for resp in valid_responses if resp['group'] == grp]
        # grp_responses = [resp for resp in valid_responses if resp['group'] == grp and resp['date_modified'] > resp['date_created'] + timedelta(minutes=10)]
        changed_answer_count = np.zeros(shape=(28,), dtype=np.int32)
        mehh_changed_answer_count = np.zeros(shape=(28,), dtype=np.int32)
        for resp in grp_responses:
            changeds = np.int32(resp[stat])
            permutation = permutations[resp['permutation']]
            changed_answer_count += changeds
            ind_stats[grp]['before_adv1'].append(np.sum(changeds[:12]))
            ind_stats[grp]['post_adv2'].append(np.sum(changeds[16:]))
            mehh_idxs = np.zeros(28,)
            mhhh_idxs = np.zeros(28,)
            mehh_idxs[np.where(permutation['q_type_perm'] == 'mehh')] = 1
            mhhh_idxs[np.where(permutation['q_type_perm'] == 'mhhh')] = 1
            mehh_idxs = np.logical_or(mehh_idxs, mhhh_idxs)
            changed_mehhs = np.logical_and(changeds, mehh_idxs)
            ind_stats[grp]['mehh_before_adv1'].append(np.sum(changed_mehhs[:12]))
            ind_stats[grp]['mehh_post_adv2'].append(np.sum(changed_mehhs[16:]))
            mehh_changed_answer_count += changed_mehhs


        x_bar = [f'{i}' for i in range(1, 29)]
        y_bar = changed_answer_count
        plot = sns.barplot(x=x_bar, y=y_bar, palette='Blues')
        plt.title(f'{stat.capitalize()}: Group {grp}')
        plt.savefig(f'./plots/{stat}_grp_{grp}.png')
        plt.close()
        summary_stats[grp] = {}
        summary_stats[grp]['before_adv1'] = np.mean(changed_answer_count[:12])
        summary_stats[grp]['post_adv2'] = np.mean(changed_answer_count[16:])
        summary_stats[grp]['mehh_before_adv1'] = np.sum(mehh_changed_answer_count[:12])/6
        # summary_stats[grp]['mehh_before_adv1'] = np.sum(mehh_changed_answer_count[:12])
        summary_stats[grp]['mehh_post_adv2'] = np.sum(mehh_changed_answer_count[16:])/6
        # summary_stats[grp]['mehh_post_adv2'] = np.sum(mehh_changed_answer_count[:16])

    pprint(summary_stats)
    # pprint(ind_stats)
    for grp in ['A', 'B', 'C', 'D']:
        ind_stats[grp]['before_adv1_mean'] = np.mean(ind_stats[grp]['before_adv1'])
        ind_stats[grp]['before_adv1_std'] = np.std(ind_stats[grp]['before_adv1'])
        ind_stats[grp]['post_adv2_mean'] = np.mean(ind_stats[grp]['post_adv2'])
        ind_stats[grp]['post_adv2_std'] = np.std(ind_stats[grp]['post_adv2'])
        _, ind_stats[grp]['mwu'] = mannwhitneyu(ind_stats[grp]['before_adv1'], ind_stats[grp]['post_adv2'])
        _, ind_stats[grp]['mwu_before_adv1_normal'] = mannwhitneyu(ind_stats[grp]['before_adv1'], np.random.normal(ind_stats[grp]['before_adv1_mean'], np.std(ind_stats[grp]['before_adv1']), 1000))
        _, ind_stats[grp]['mwu_post_adv2_normal'] = mannwhitneyu(ind_stats[grp]['post_adv2'], np.random.normal(ind_stats[grp]['post_adv2_mean'], np.std(ind_stats[grp]['post_adv2']), 1000))
        print('test')
    print('test')
    print(f"POST: A vs B = {mannwhitneyu(ind_stats['A']['post_adv2'], ind_stats['B']['post_adv2'], alternative=alternative)}")
    print(f"POST: A vs C = {mannwhitneyu(ind_stats['A']['post_adv2'], ind_stats['C']['post_adv2'], alternative=alternative)}")
    print(f"POST: B vs D = {mannwhitneyu(ind_stats['B']['post_adv2'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    print(f"POST: C vs D = {mannwhitneyu(ind_stats['C']['post_adv2'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    print(f"PRE: A vs B = {mannwhitneyu(ind_stats['A']['before_adv1'], ind_stats['B']['before_adv1'], alternative=alternative)}")
    print(f"PRE: A vs C = {mannwhitneyu(ind_stats['A']['before_adv1'], ind_stats['C']['before_adv1'], alternative=alternative)}")
    print(f"PRE: B vs D = {mannwhitneyu(ind_stats['B']['before_adv1'], ind_stats['D']['before_adv1'], alternative=alternative)}")
    print(f"PRE: C vs D = {mannwhitneyu(ind_stats['C']['before_adv1'], ind_stats['D']['before_adv1'], alternative=alternative)}")
    print(f"PRE vs POST: A = {mannwhitneyu(ind_stats['A']['before_adv1'], ind_stats['A']['post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: B = {mannwhitneyu(ind_stats['B']['before_adv1'], ind_stats['B']['post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: C = {mannwhitneyu(ind_stats['C']['before_adv1'], ind_stats['C']['post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: D = {mannwhitneyu(ind_stats['D']['before_adv1'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    print('mehh')
    print(f"POST: A vs B = {mannwhitneyu(ind_stats['A']['mehh_post_adv2'], ind_stats['B']['mehh_post_adv2'], alternative=alternative)}")
    print(f"POST: A vs C = {mannwhitneyu(ind_stats['A']['mehh_post_adv2'], ind_stats['C']['mehh_post_adv2'], alternative=alternative)}")
    print(f"POST: B vs D = {mannwhitneyu(ind_stats['B']['mehh_post_adv2'], ind_stats['D']['mehh_post_adv2'], alternative=alternative)}")
    print(f"POST: C vs D = {mannwhitneyu(ind_stats['C']['mehh_post_adv2'], ind_stats['D']['mehh_post_adv2'], alternative=alternative)}")
    print(f"PRE: A vs B = {mannwhitneyu(ind_stats['A']['mehh_before_adv1'], ind_stats['B']['mehh_before_adv1'], alternative=alternative)}")
    print(f"PRE: A vs C = {mannwhitneyu(ind_stats['A']['mehh_before_adv1'], ind_stats['C']['mehh_before_adv1'], alternative=alternative)}")
    print(f"PRE: B vs D = {mannwhitneyu(ind_stats['B']['mehh_before_adv1'], ind_stats['D']['mehh_before_adv1'], alternative=alternative)}")
    print(f"PRE: C vs D = {mannwhitneyu(ind_stats['C']['mehh_before_adv1'], ind_stats['D']['mehh_before_adv1'], alternative=alternative)}")
    print(f"PRE vs POST: A = {mannwhitneyu(ind_stats['A']['mehh_before_adv1'], ind_stats['A']['mehh_post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: B = {mannwhitneyu(ind_stats['B']['mehh_before_adv1'], ind_stats['B']['mehh_post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: C = {mannwhitneyu(ind_stats['C']['mehh_before_adv1'], ind_stats['C']['mehh_post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: D = {mannwhitneyu(ind_stats['D']['mehh_before_adv1'], ind_stats['D']['mehh_post_adv2'], alternative=alternative)}")
    # print(f"wcx POST: A vs B = {wilcoxon(ind_stats['A']['post_adv2'], ind_stats['B']['post_adv2'], alternative=alternative)}")
    # print(f"wcx POST: A vs C = {wilcoxon(ind_stats['A']['post_adv2'], ind_stats['C']['post_adv2'], alternative=alternative)}")
    # print(f"wcx POST: B vs D = {wilcoxon(ind_stats['B']['post_adv2'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    # print(f"wcx POST: C vs D = {wilcoxon(ind_stats['C']['post_adv2'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    # print(f"wcx PRE: A vs B = {wilcoxon(ind_stats['A']['before_adv1'], ind_stats['B']['before_adv1'], alternative=alternative)}")
    # print(f"wcx PRE: A vs C = {wilcoxon(ind_stats['A']['before_adv1'], ind_stats['C']['before_adv1'], alternative=alternative)}")
    # print(f"wcx PRE: B vs D = {wilcoxon(ind_stats['B']['before_adv1'], ind_stats['D']['before_adv1'], alternative=alternative)}")
    # print(f"wcx PRE: C vs D = {wilcoxon(ind_stats['C']['before_adv1'], ind_stats['D']['before_adv1'], alternative=alternative)}")
    print(f"wcx PRE vs POST: A = {wilcoxon(ind_stats['A']['before_adv1'], ind_stats['A']['post_adv2'], alternative=alternative)}")
    print(f"wcx PRE vs POST: B = {wilcoxon(ind_stats['B']['before_adv1'], ind_stats['B']['post_adv2'], alternative=alternative)}")
    print(f"wcx PRE vs POST: C = {wilcoxon(ind_stats['C']['before_adv1'], ind_stats['C']['post_adv2'], alternative=alternative)}")
    print(f"wcx PRE vs POST: D = {wilcoxon(ind_stats['D']['before_adv1'], ind_stats['D']['post_adv2'], alternative=alternative)}")

    summary_stats = {}
    ind_stats = {}
    for grp in ['A', 'B', 'C', 'D']:
        ind_stats[grp] = {'before_adv1': [], 'post_adv2': []}
        q_id_avgs = np.zeros((28,), dtype=np.float32)

        grp_responses = [resp for resp in valid_responses if resp['group'] == grp]
        # grp_responses = [resp for resp in valid_responses if resp['group'] == grp and resp['date_modified'] > resp['date_created'] + timedelta(minutes=10)]
        for resp in grp_responses:
            permutation = permutations[resp['permutation']]
            changeds = np.int32(resp[stat])
            q_id_avgs += changeds[permutation['Index_orig'].values]

        q_id_avgs /= len(grp_responses)
        q_num_avgs = np.zeros((28,), dtype=np.float32)
        for resp in grp_responses:
            changeds = np.int32(resp[stat])
            permutation = permutations[resp['permutation']]
            perm_id = resp['permutation']
            balanced_changeds = changeds - q_id_avgs[permutation['Index_orig'].values]
            q_num_avgs += balanced_changeds
            ind_stats[grp]['before_adv1'].append(np.sum(balanced_changeds[:12]))
            ind_stats[grp]['post_adv2'].append(np.sum(balanced_changeds[16:]))
            # print('test')

        x_bar = [f'{i}' for i in range(1, 29)]
        y_bar = q_num_avgs
        y_bar = [sum(q_num_avgs[:i]) for i in range(len(y_bar))]
        plot = sns.barplot(x=x_bar, y=y_bar, palette='Blues')
        plt.title(f'{stat.capitalize().replace("_", " ")} (order balanced): Group {grp}')
        plt.savefig(f'./plots/ob_{stat}_grp_{grp}.png')
        plt.close()
        summary_stats[grp] = {}
        summary_stats[grp]['before_adv1'] = np.mean(q_num_avgs[:12])
        summary_stats[grp]['post_adv2'] = np.mean(q_num_avgs[16:])

    pprint(summary_stats)
    print(f"POST: A vs B = {mannwhitneyu(ind_stats['A']['post_adv2'], ind_stats['B']['post_adv2'], alternative=alternative)}")
    print(f"POST: A vs C = {mannwhitneyu(ind_stats['A']['post_adv2'], ind_stats['C']['post_adv2'], alternative=alternative)}")
    print(f"POST: B vs D = {mannwhitneyu(ind_stats['B']['post_adv2'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    print(f"POST: C vs D = {mannwhitneyu(ind_stats['C']['post_adv2'], ind_stats['D']['post_adv2'], alternative=alternative)}")
    print(f"PRE: A vs B = {mannwhitneyu(ind_stats['A']['before_adv1'], ind_stats['B']['before_adv1'], alternative=alternative)}")
    print(f"PRE: A vs C = {mannwhitneyu(ind_stats['A']['before_adv1'], ind_stats['C']['before_adv1'], alternative=alternative)}")
    print(f"PRE: B vs D = {mannwhitneyu(ind_stats['B']['before_adv1'], ind_stats['D']['before_adv1'], alternative=alternative)}")
    print(f"PRE: C vs D = {mannwhitneyu(ind_stats['C']['before_adv1'], ind_stats['D']['before_adv1'], alternative=alternative)}")
    print(f"PRE vs POST: A = {mannwhitneyu(ind_stats['A']['before_adv1'], ind_stats['A']['post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: B = {mannwhitneyu(ind_stats['B']['before_adv1'], ind_stats['B']['post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: C = {mannwhitneyu(ind_stats['C']['before_adv1'], ind_stats['C']['post_adv2'], alternative=alternative)}")
    print(f"PRE vs POST: D = {mannwhitneyu(ind_stats['D']['before_adv1'], ind_stats['D']['post_adv2'], alternative=alternative)}")

    # pprint(ind_stats)
    print('test')










if __name__ == '__main__':
    analysis()