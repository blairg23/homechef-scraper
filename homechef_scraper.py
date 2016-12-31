'''
Author: Blair Gemmer
Date: 2016-10-14
Description:

Scrapes homechef website for all recipe cards in PDF form.

If it doesn't find a PDF link (some of the older recipes don't have them),

it will create a PDF out of the webpage.

Must have valid login credentials to get recipes older than one week.

'''

# System stuff:
import os
import sys
import shutil

# Request stuff:
import requests
from requests.auth import HTTPBasicAuth

# Formatting stuff:
import json
from bs4 import BeautifulSoup
#import pdfkit

# Date stuff:
from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import *

# Downloading stuff:
import wget

# Misc:
import uuid

# My custom creds module
from creds import credentials 

def next_date(date_string=None, date_object=None):
    '''
    Returns the next date 7 days from this date.
    '''
    if date_string != None:
        date_object = parser.parse(date_string)
    return date_object + relativedelta(days=+7)

def format_date(date_object=None, date_format='%d-%b-%Y'):
    '''
    Formats the given date object like "01-jan-2016".
    '''
    return date_object.strftime(date_format).lower()


def perform_requests(formatted_date=None, auth=None, responses={}, saved_endpoints=[]):
    '''
    Add data to a response object by performing requests, add that
    response object to our responses object, and finally return the 
    responses object.
    '''
    print('[PERFORMING REQUEST] For current date: {formatted_date}...'.format(formatted_date=formatted_date))

    base_url = 'https://www.homechef.com'
    endpoint = '/menus/' + formatted_date
    request_url = base_url + endpoint
    
    response = requests.get(request_url, auth=HTTPBasicAuth(auth[0], auth[1]))
    
    endpoints = []

    if response.status_code == 200:
        html_doc = response.content
        soup = BeautifulSoup(html_doc, 'html.parser')

        for anchor in soup.find_all('a'):
            if 'meals' in anchor['href']:
                endpoints.append(str(anchor['href']))
    
    for endpoint in set(endpoints):
        if endpoint in saved_endpoints:
            print('[WARNING] Endpoint {endpoint} found. Skipping...'.format(endpoint=endpoint))
            continue

        pdf_list = []

        response_object = {}
        response_object['id'] = str(uuid.uuid4())
        response_object['date'] = formatted_date
        response_object['endpoint'] = endpoint
        response_object['pdfs'] = []

        request_url = base_url + endpoint
        response = requests.get(request_url, auth=HTTPBasicAuth(auth[0], auth[1]))

        if response.status_code == 200:
            html_doc = response.content
            soup = BeautifulSoup(html_doc, 'html.parser')

            for anchor in soup.find_all('a'):
                if 'pdf' in anchor['href']:
                    pdf_list.append(anchor['href'])

        for pdf in set(pdf_list):
            response_object['pdfs'].append(pdf)

        responses['data'].append(response_object)

    print('\n')
    return responses


def download_file(url=None, output_filepath=None):
    #local_filename = url.split('/')[-1]
    # NOTE the stream=True parameter
    response = requests.get(url, stream=True)
    with open(output_filepath, 'wb') as outfile:
        for chunk in response.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                outfile.write(chunk)
                #f.flush() commented by recommendation from J.F.Sebastian    


def download_files(file_list_dict=None, output_folder=None):
    '''
    Downloads a list of files from a dictionary with
    <key:value> pairs of type <date:list_of_files>.
    '''
    print('[DOWNLOADING] List of files...')
    for date,url_list in file_list_dict.items():
        parsed_date = parser.parse(date)
        formatted_date = format_date(date_object=parsed_date, date_format='%Y%m%d')
        output_directory = os.path.join(output_folder, formatted_date)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        for url in url_list:
            filename = url.split('/')[-1]
            output_filepath = os.path.join(output_directory, filename)          
            # No reason to download a file twice:
            if not os.path.exists(output_filepath):
                print('[DOWNLOADING] {url} to {filepath}...'.format(url=url, filepath=output_filepath))
                download_file(url, output_filepath=output_filepath)
                alt_file_directory = os.path.join(output_folder, 'all_pdfs')
                alt_filepath = os.path.join(alt_file_directory, filename)
                if not os.path.exists(alt_file_directory):
                    os.makedirs(alt_file_directory)
                print('[COPYING] {filename} to {alt_filepath}...\n'.format(filename=filename, alt_filepath=alt_filepath))
                shutil.copy2(output_filepath, alt_filepath)
            else:
                print('[WARNING] {filepath} exists. Skipping...\n'.format(filepath=output_filepath))


def get_file_list_dict(input_dict=None):
    '''
    Get a list of files from an input dictionary.
    '''
    print('[GATHERING] List of saved PDF files...')
    file_list_dict = {}

    for data_item in input_dict['data']:
        date = data_item['date']
        pdfs = data_item['pdfs']
        if not str(date) in file_list_dict.keys():
            file_list_dict[str(date)] = []
        else:
            file_list_dict[str(date)].extend(pdfs)
    
    return file_list_dict

def get_responses(json_file='pdf_data.json'):
    '''
    If JSON file exists, returns dictionary containing contents.
    Otherwise, returns empty dictionary with data object.
    '''
    if os.path.exists(json_file):
        with open(json_file) as infile:
            responses = json.load(infile)
        print('[READING] JSON from {json_file}...\n'.format(json_file=json_file))
    else:
        responses = {}
        responses['data'] = []
        print('[CREATING] Empty JSON object...\n')

    return responses


def get_saved_endpoints(input_dict=None):
    '''
    Get a list of saved endpoints from an input dictionary.
    '''
    print('[GATHERING] Previously saved endpoints...')
    return [data_item['endpoint'] for data_item in input_dict['data']]


def get_latest_request_date(input_dict=None):
    '''
    Get the latest requested date from the input dictionary to damped 
    previously created requests.
    '''
    print('[GATHERING] Latest created date...')
    return max([parser.parse(data_item['date']) for data_item in input_dict['data']])


def write_json(input_dict=None, output_file='pdf_data.json'):
    '''
    Takes given dictionary and writes to json output file.
    '''
    with open(output_file, 'w+') as outfile:
        json.dump(input_dict, outfile)
    print('[WRITING] Dictionary to file {output_file}...'.format(output_file=output_file))


if __name__ == '__main__':
    auth = [credentials['username'], credentials['password']]
    earliest_date = '17-mar-2014'
    data_output_directory = 'data'
    pdf_output_directory = os.path.join(data_output_directory, 'pdfs')
    data_filename = os.path.join(data_output_directory, 'pdf_data.json')

    responses = get_responses(json_file=data_filename)

    if not os.path.exists(data_output_directory):
        os.makedirs(data_output_directory)


    # Gather previous data if it exists:
    saved_endpoints = []
    if responses['data'] != []:
        # Get all previously gathered endpoints:
        saved_endpoints = get_saved_endpoints(input_dict=responses)
        # Also get the last request date we grabbed:
        latest_request_date = get_latest_request_date(input_dict=responses)
        parsed_date = latest_request_date
    else:
        parsed_date = parser.parse(earliest_date)
    formatted_date = format_date(parsed_date)
    
    while parsed_date < (datetime.now() + relativedelta(days=+14)):
        responses = perform_requests(
                                        formatted_date=formatted_date,
                                        auth=auth,
                                        responses=responses,
                                        saved_endpoints=saved_endpoints
                                    )

        # Update to new values (next week):
        new_parsed_date = next_date(date_object=parsed_date)
        new_formatted_date = format_date(new_parsed_date)

        # Update the old values to the new ones:
        formatted_date = new_formatted_date
        parsed_date = new_parsed_date

    write_json(input_dict=responses, output_file=data_filename)

    file_list_dict = get_file_list_dict(input_dict=responses)

    download_files(file_list_dict=file_list_dict, output_folder=pdf_output_directory)