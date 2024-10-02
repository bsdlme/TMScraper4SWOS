# Transfermarkt Scraper 4 SWOS

This Python script scrapes player data from Transfermarkt for a specific league (default: Premier League). It extracts club and player details, including market values, nationalities, and positions, and saves them into a CSV file.

## Features

- Scrapes player information from clubs in a given league.
- Extracts details such as player name, nationality, position, market value, and URLs to the player's profile.
- Outputs the data into a CSV file for further analysis.

## Requirements

- Python 3.x
- Required libraries: `requests`, `beautifulsoup4`, `pandas`, `tqdm`, `anyascii`


You can install the required dependencies using:

```bash
pip install -r requirements.txt
```

## License

BSD 2-Clause License

## Usage

usage: ```bash [-h] [-u CLUBS_URL] [-n NUMBER_OF_CLUBS]

Scrape and download club and player data from Transfermarkt for use in SWOS

options:
  -h, --help            show this help message and exit
  -u CLUBS_URL, --clubs-url CLUBS_URL
                        URL of the overview page of the league
  -n NUMBER_OF_CLUBS, --number-of-clubs NUMBER_OF_CLUBS
                        Number of clubs to download. Defaults to 1.
TMScraper4SWOS.py
```
