import requests
import json
from pprint import pprint
import pickle
from datetime import datetime
from pathlib import Path
import os


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


def pull_all_surveys():
    ids = get_survey_ids()
    filesafe_datetime = datetime.now().strftime('%m_%d_%H_%M_%S')
    survey_pulls_dir = Path('./monkey_data/survey_pulls/')
    latest_id = max([int(p.parts[-1]) for p in list(survey_pulls_dir.glob('*'))])
    target_dir = f'{str(survey_pulls_dir)}/{latest_id+1}'
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    surveys_dir = f'./monkey_data/survey_pulls/'
    responses = {}
    for name, id in ids.items():
        response = pull_survey_data(id)
        pickle.dump(response, open(f'{target_dir}/{name}.pkl', 'wb'))
        responses[name] = response

    open(f'{filesafe_datetime}.time', 'a')
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
    pickle.dump(individual_responses, open(f'{survey_pulls_dir}/{latest_id}/all_individuals.pkl', 'wb'))
    print('test')
    all_modified_dates = []
    all_created_dates = []
    for individual in individual_responses:
        modified_str = individual['date_modified']
        created_str = individual['date_created']
        modified_dt = datetime.strptime(modified_str, '%Y-%m-%dT%H:%M:%S+00:00')
        created_dt = datetime.strptime(created_str, '%Y-%m-%dT%H:%M:%S+00:00')
        all_modified_dates.append(modified_dt)
        all_created_dates.append(created_dt)

    most_recent_hits = sorted(all_modified_dates, reverse=True)
    most_recently_created = sorted(all_created_dates, reverse=True)
    page_path = sorted([(datetime.strptime(response['date_created'], '%Y-%m-%dT%H:%M:%S+00:00'), len(response['page_path'])) for
            response in individual_responses], key=lambda x: x[0], reverse=True)
    print('test')





def pull_survey_data(survey_id):
    response = make_get_request(f'/v3/surveys/{survey_id}/responses/bulk?per_page=100')
    # pickle.dump(response, open(f'./monkey_data/'))
    return response


if __name__ == '__main__':
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
