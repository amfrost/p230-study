import requests
import json
from pprint import pprint
import pickle
from datetime import datetime, timedelta
from pathlib import Path
import os
import numpy as np


def prepare_request(endpoint):
    client = requests.session()
    headers = {
        'Authorization': 'bearer %s' % 'yILhrIQNpmJHyxVOAlOhIybNQ.cjHt1PY0sw8KkKhUJOnkG06TFO4ClmMzkwun-P9yoaPIGWJpBp51yBoicL5W400ntNXh.98bJwMs0M-6BwFOG-0HjxiLt6S3ytnNtC',
        'Content-Type': 'application/json'
    }
    HOST = 'https://api.surveymonkey.com'
    uri = f'{HOST}{endpoint}'
    return client, uri, headers

def make_get_request(endpoint):
    client, uri, headers = prepare_request(endpoint)
    response = client.get(uri, headers=headers)
    return response

def get_survey_ids():
    v3_surveys_response = pickle.load(open('./monkey_data/GET_v3-surveys_response.pkl', 'rb'))
    response = json.loads(v3_surveys_response.text)
    print('test')
    data = response['data']
    grp_a = [survey for survey in data if survey['title'] == 'Dog Identification - Group A'][0]
    grp_b = [survey for survey in data if survey['title'] == 'Dog Identification - Group B'][0]
    grp_c = [survey for survey in data if survey['title'] == 'Dog Identification - Group C'][0]
    grp_d = [survey for survey in data if survey['title'] == 'Dog Identification - Group D'][0]

    ids = {'A': grp_a['id'], 'B': grp_b['id'], 'C': grp_c['id'], 'D': grp_d['id']}
    return ids

def get_survey_details():
    survey_ids = get_survey_ids()
    details = {}
    for group, id in survey_ids.items():
        survey_details_file = f'./monkey_data/GET_grp-{group}-details_response.pkl'
        if not os.path.exists(survey_details_file):
            response = make_get_request(f'/v3/surveys/{id}/details')
            pickle.dump(response, open(survey_details_file, 'wb'))
        else:
            response = pickle.load(open(survey_details_file, 'rb'))
        details[group] = response
    return details

def pull_all_surveys():
    ids = get_survey_ids()
    filesafe_datetime = datetime.now().strftime('%m_%d_%H_%M_%S')
    survey_pulls_dir = Path('./monkey_data/survey_pulls/')
    latest_id = max([int(p.parts[-1]) for p in list(survey_pulls_dir.glob('*'))])
    target_dir = f'{str(survey_pulls_dir)}/{latest_id+1}'
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # surveys_dir = f'./monkey_data/survey_pulls/'
    responses = {}
    for name, id in ids.items():
        response = pull_survey_data(id)
        pickle.dump(response, open(f'{target_dir}/{name}.pkl', 'wb'))
        responses[name] = response

    open(f'{target_dir}/{filesafe_datetime}.time', 'a')
    pickle.dump(responses, open(f'{target_dir}/all_responses.pkl', 'wb'))

def load_latest_survey_pull():
    survey_pulls_dir = Path('./monkey_data/survey_pulls')
    latest_id = max([int(p.parts[-1]) for p in list(survey_pulls_dir.glob('*'))])

    all_responses = pickle.load(open(f'{survey_pulls_dir}/{latest_id}/all_responses.pkl', 'rb'))
    individual_responses = []
    for name, response in all_responses.items():
        data = json.loads(response.text)['data']
        for individual in data:
            individual['group'] = name
            individual_responses.append(individual)
    print('test')
    all_modified_dates = []
    all_created_dates = []

    livetimes = [Path(f'./questions/permutations/perm_{i}/livetimes.txt') for i in range(len(list(Path('./questions/permutations').glob('perm_*'))))]
    livetimes = [open(pd, 'r').read() for pd in livetimes]
    livetimes = [datetime.strptime(livetimes[i], '%d/%m/%Y %H%M') for i in range(len(livetimes))]
    livetimes.append(datetime.now())



    for individual in individual_responses:
        modified_str = individual['date_modified']
        created_str = individual['date_created']
        modified_dt = datetime.strptime(modified_str, '%Y-%m-%dT%H:%M:%S+00:00')
        created_dt = datetime.strptime(created_str, '%Y-%m-%dT%H:%M:%S+00:00')
        all_modified_dates.append(modified_dt)
        all_created_dates.append(created_dt)
        individual['date_modified'] = modified_dt
        individual['date_created'] = created_dt
        perm = -1
        for i in range(len(livetimes)):
            if created_dt >= livetimes[i] and modified_dt < livetimes[i+1]:
                perm = i
                break
        individual['permutation'] = perm

    pickle.dump(individual_responses, open(f'{survey_pulls_dir}/{latest_id}/all_individuals.pkl', 'wb'))

    most_recent_hits = sorted(all_modified_dates, reverse=True)
    most_recently_created = sorted(all_created_dates, reverse=True)
    # page_path = sorted([(datetime.strptime(response['date_created'], '%Y-%m-%dT%H:%M:%S+00:00'), len(response['page_path'])) for
    #         response in individual_responses], key=lambda x: x[0], reverse=True)
    # print('test')

    completions = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for resp in individual_responses:
        if resp['response_status'] == 'completed' and resp['permutation'] != -1:
            completions[resp['group']] += 1

    now = datetime.now()
    last_30 = timedelta(minutes=30)

    recently_modified = sorted([resp['date_modified'] for resp in individual_responses if resp['date_modified'] > (now - last_30)], reverse=True)
    recently_created = sorted([resp['date_created'] for resp in individual_responses if resp['date_modified'] > (now - last_30)], reverse=True)
    perm_counts = [(i, [resp['permutation'] for resp in individual_responses if resp['response_status']=='completed'].count(i)) for i in range(len(list(Path('./questions/permutations').glob('perm_*'))))]
    sorted_responses = sorted(individual_responses, key=lambda r:r['date_modified'], reverse=True)
    print('test')




def pull_survey_data(survey_id):
    response = make_get_request(f'/v3/surveys/{survey_id}/responses/bulk?per_page=100')
    # pickle.dump(response, open(f'./monkey_data/'))
    return response


if __name__ == '__main__':
    # resp = make_get_request(f'/v3/surveys')
    pull_all_surveys()
    load_latest_survey_pull()
    # ids = get_survey_ids()
    # print('test')
    # response = make_get_request(f'/v3/surveys/{ids["A"]}/responses/bulk?per_page=100')
    # print('test')
    # ENDPOINT = '/surveys/302648794/responses/bulk?per_page=100'
    # response = client.post(uri, headers=headers, data=json.dumps(data))

    # response = make_get_request(ENDPOINT)

    # response_json = response.json()
    # pprint(response_json)
    # print(response_json)
