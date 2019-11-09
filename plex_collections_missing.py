#!/usr/bin/env python3

import re
import os
import yaml
import requests
import xml.etree.ElementTree as ElementTree
import click
import pprint as pretty
import logging
from datetime import datetime
from plexapi.server import PlexServer
from tmdbv3api import TMDb, Collection, Movie

CONFIG_FILE = 'config.yaml'
DEBUG = False
DRY_RUN = False
LIBRARY_IDS = False
CONFIG = dict()
TMDB = TMDb()


def init(debug=False, dry_run=False, library_ids=False):
    global DEBUG
    global DRY_RUN
    global LIBRARY_IDS
    global CONFIG
    global TMDB

    DEBUG = debug
    DRY_RUN = dry_run
    LIBRARY_IDS = library_ids

    if not DEBUG:
        logging.getLogger('tmdbv3api.tmdb').disabled = True

    with open(CONFIG_FILE, 'r') as stream:
        try:
            CONFIG = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    CONFIG['headers'] = {'X-Plex-Token': CONFIG['plex_token']}

    TMDB.api_key = CONFIG['tmdb_key']
    TMDB.wait_on_rate_limit = True
    TMDB.language = 'en'

    if DEBUG:
        print('CONFIG: ')
        pretty.pprint(CONFIG)


def setup():
    try:
        data = dict()
        data['plex_url'] = click.prompt('Please enter your Plex URL', type=str)
        data['plex_token'] = click.prompt('Please enter your Plex Token', type=str)
        data['tmdb_key'] = click.prompt('Please enter your TMDB API Key', type=str)

        with open(CONFIG_FILE, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)
    except (KeyboardInterrupt, SystemExit):
        raise


def check():
    plex = PlexServer(CONFIG['plex_url'], CONFIG['plex_token'])
    plex_sections = plex.library.sections()

    for plex_section in plex_sections:
        if plex_section.type != 'movie':
            continue

        if LIBRARY_IDS and int(plex_section.key) not in LIBRARY_IDS:
            print('ID: %s Name: %s - SKIPPED' % (str(plex_section.key).ljust(4, ' '), plex_section.title))
            continue

        print('ID: %s Name: %s' % (str(plex_section.key).ljust(4, ' '), plex_section.title))
        create_file(plex_section.title)
        plex_collections = plex_section.collection()

        # Set TMDB language for section
        TMDB.language = plex_section.language
        total = len(plex_collections)

        for count, plex_collection in enumerate(plex_collections):
            check_collection(plex_collection, plex_section.title, count + 1, total)


def check_collection(plex_collection, section_title, count, total):
    tmdb_collection_id = get_tmdb_collection_id(plex_collection)
    collection = Collection().details(collection_id=tmdb_collection_id)
    tmdb_ids = get_tmdb_ids(plex_collection)
    curent_year = datetime.now().year
    missing = []

    for part in collection.parts:
        if not part.get('release_date'):
            continue
        if part.get('id') not in tmdb_ids and int(part.get('release_date')[:4]) <= curent_year:
            missing.append(part)

    if not missing:
        click.secho('%s %s [%s/%s]' % (u'\u2713', plex_collection.title, count, total), fg='green')
        if not DRY_RUN:
            append_file(section_title, '%s %s [%s/%s]\n' % ('\u2713', plex_collection.title, count, total))
        return

    click.secho('%s %s [%s/%s]' % (u'\u2717', plex_collection.title, count, total), fg='red')
    if not DRY_RUN:
        append_file(section_title, '%s %s [%s/%s]\n' % ('\u2717', plex_collection.title, count, total))
    for x in missing:
        click.secho('  - %s (%s)' % (x.get('title'), x.get('release_date')[:4]), fg='red')
        if not DRY_RUN:
            append_file(section_title, '  - %s (%s)\n' % (x.get('title'), x.get('release_date')[:4]))


def create_file(collection_name):
    file = open('missing_' + str(collection_name).replace(" ", "_") + ".txt", "w", encoding='utf-8')
    file.write("Missing Movies from %s Collections.\n" % collection_name)
    file.close()


def append_file(collection_name, content):
    file = open('missing_' + str(collection_name).replace(" ", "_") + ".txt", "a", encoding='utf-8')
    file.write(content)
    file.close()


def list_libraries():
    plex = PlexServer(CONFIG['plex_url'], CONFIG['plex_token'])
    plex_sections = plex.library.sections()

    for plex_section in plex_sections:
        if plex_section.type != 'movie':
            continue

        print('ID: %s Name: %s' % (str(plex_section.key).ljust(4, ' '), plex_section.title))


def get_plex_data(url):
    r = requests.get(url, headers=CONFIG['headers'])
    return ElementTree.fromstring(r.text)


def get_tmdb_collection_id(plex_collection):
    for movie in plex_collection.children:
        match = get_tmdb_id(movie.guid)

        if not match:
            continue

        movie = Movie().details(movie_id=match.group())

        if not movie.entries.get('belongs_to_collection'):
            return '-1'

        return movie.entries.get('belongs_to_collection').get('id')


def get_tmdb_ids(plex_collection):
    tmdb_ids = []

    for movie in plex_collection.children:
        match = get_tmdb_id(movie.guid)

        if match:
            tmdb_id = match.group()
            if tmdb_id[:2] == 'tt':
                movie = Movie().details(movie_id=tmdb_id)
                tmdb_id = movie.id

            tmdb_ids.append(tmdb_id)

    return tmdb_ids


def get_tmdb_id(guid):
    match = False

    if guid.startswith('com.plexapp.agents.imdb://'):  # Plex Movie agent
        match = re.search(r'tt[0-9]\w+', guid)
    elif guid.startswith('com.plexapp.agents.themoviedb://'):  # TheMovieDB agent
        match = re.search(r'[0-9]\w+', guid)

    return match


@click.group()
def cli():
    if not os.path.isfile(CONFIG_FILE):
        click.confirm('Configuration not found, would you like to set it up?', abort=True)
        setup()
        exit(0)
    pass


@cli.command('setup', help='Set Configuration Values')
def command_setup():
    setup()


@cli.command('run', help='Check Plex Collections for missing movies',
             epilog="eg: plex_collections_missing.py run --dry-run --library=5 --library=8")
@click.option('--debug', '-v', default=False, is_flag=True)
@click.option('--dry-run', '-d', default=False, is_flag=True)
@click.option('--library', default=False, multiple=True, type=int,
              help='Library ID to Update (Default all movie libraries)')
def run(debug, dry_run, library):
    init(debug, dry_run, library)
    print('\r\nChecking Collection(s)')
    check()


@cli.command('list', help='List all Libraries')
def command_update_posters():
    init()
    print('\r\nUpdating Collection Posters')
    list_libraries()


if __name__ == "__main__":
    cli()
