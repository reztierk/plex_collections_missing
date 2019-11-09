# plex_collections_missing
This script is intended to be used to check your Plex collections for missing movies.

# Requirements
Built for Python 3.

# Installation
    git clone https://github.com/reztierk/plex_collections_missing.git
    cd plex_collections_missing
    pip install -r requirements.txt

# Usage

### setup
Used to set the required configuration values (triggered automatically of config.yaml is not found during script initialization).

    python plex_collections_missing.py setup

Required values:
 - Plex URL 
    - URL of the Plex instance you wish to use (eg. http://localhost:32400)
 - Plex Token
    - Token to be used for authenticated with Plex (see: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
 - TMDB Key
    - API key to be used with TMDB (see: https://developers.themoviedb.org/3/getting-started/introduction)

### list
Used to list all available Libraries (useful for easily obtaining a libraries ID)

    python plex_collections_missing.py list
    
### run
Check Collections, by default it will check each collection in each movie library and generate a text file 
(`missing_<Library_Name>.txt`) with the findings. It attempts to limit the output to only movies with a release date 
less than or equal to the current year. Can also be used with `--dry-run` to test without generating the output file, 
or `--library` to check only a specific libraries collections.

    # Run
    python plex_collections_missing.py run
    
    # Just posters, dry run and filter by library ID's 
    python plex_collections_missing.py run posters --dry-run --library=5 --library=8
    

Options: 
    
    -v, --debug
    -d, --dry-run
    --library INTEGER  Library ID to Update (Default all movie libraries)

