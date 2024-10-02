# BSD 2-Clause License
#
# Copyright (c) 2024, Lars Engels <lars.engels@0x20.net>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import re
import time
import argparse
from datetime import datetime
from anyascii import anyascii

import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm  # Progress bar library


def get_html(url, timeout=30):
    """
    Fetch HTML content from the given URL.
    """
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.3')
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()  # Raise exception for HTTP errors
    return response.content

def extract_player_details(player_stats_url, position_tm):
    """
    Extract relevant player details (minutes played, goals, etc.) from the player's detail page
    """
    html = get_html(player_stats_url)
    soup = BeautifulSoup(html, 'html.parser')
    stats_header = soup.find_all("h2", {"class": "content-box-headline"})
    # Goalkepers and fielders show different stats. We need two seperate lists
    keys_goalkeeper = ["season", "empty", "games", "goals", "yellow_cards", "yellow_red_cards", "red_cards", "goals_conceded", "clean_sheets", "minutes"]
    keys_fielder = ["season", "empty", "games", "goals", "assists", "yellow_cards", "yellow_red_cards", "red_cards", "minutes"]

    if (position_tm) == 'Goalkeeper':
        keys = keys_goalkeeper
    else:
        keys = keys_fielder

    # Some players don't have stats for the current season.
    # Seting all stats to '-' and skip the player.
    found_stats = False
    for header in stats_header:
        if header.text.strip() == "Stats 24/25": # To do: make the current season a variable
            found_stats = True
    if found_stats is False:
        player_stats = {key: "-" for key in keys_goalkeeper + keys_fielder}
        return player_stats

    # Find the div containing player statistics
    tds = soup.find("table", {"class": "items"}).find("tfoot").find_all("td")
    player_stats = {key: td.get_text(strip=False) for key, td in zip(keys, tds)}
    if player_stats.get('minutes'):
        player_stats['minutes'] = player_stats['minutes'].replace("'", "").replace(".", "")
    # Initialise missing stats with '-'
    for key in keys_goalkeeper + keys_fielder:
        if not player_stats.get(key):
            player_stats[key] = "-"
    return player_stats

def extract_player_data(row, club_name, club_url):
    """
    Extract relevant player data from a table row.
    """
    player_name = str(anyascii(row.find("td", {"class": "hauptlink"}).text.strip()))
    player_number = row.find("div", {"class": "rn_nummer"}).text.strip()
    player_url = "https://transfermarkt.com" + row.find("td", {"class": "hauptlink"}).find("a").get("href")
    player_stats_url = player_url.replace('profil', 'leistungsdaten')
    market_value_tm = row.find("td", {"class": "rechts hauptlink"}).text.strip()

    # Extract position and nationality
    regex = re.compile(r'^\n')
    position_tm = row.find("td", string=regex).text.strip()
    nationality = row.find("img", {"class": "flaggenrahmen"}).get("title")

    player_stats = extract_player_details(player_stats_url, position_tm)

    # Convert position from Transfermarkt to SWOS format
    position_tm_to_swos = {
        'Attacking Midfield': 'M', 'Central Midfield': 'M', 'Centre-Back': 'D',
        'Centre-Forward': 'A', 'Defensive Midfield': 'M', 'Goalkeeper': 'G',
        'Left Midfield': 'M', 'Left Winger': 'LW', 'Left-Back': 'LB',
        'Right Midfield': 'M', 'Right Winger': 'RW', 'Right-Back': 'RB'
    }

    position_swos = position_tm_to_swos.get(position_tm, 'Unknown')
    market_value_swos, stars = get_value_swos_and_stars(market_value_tm, position_swos)
    nationality_swos = get_nationality(nationality)

    return {
        'Club': club_name,
        'Club URL': club_url,
        'Schedule': f"{club_url.replace('startseite', 'spielplan')}/saison_id/{datetime.now().year}",
        'Player Number': player_number,
        'Player': player_name,
        'Player URL': player_url,
        'Nationality': nationality,
        'Nationality SWOS': nationality_swos,
        'Position TM': position_tm,
        'Position SWOS': position_swos,
        'Market Value TM': market_value_tm, 
        'Market Value SWOS': market_value_swos,
        'Stars': stars,
        'Games': player_stats['games'],
        'Minutes played': player_stats['minutes'],
        'Goals': player_stats['goals'],
        'Assists': player_stats['assists'],
        'Yellow Cards': player_stats['yellow_cards'],
        'Yellow Red Cards': player_stats['yellow_red_cards'],
        'Red Cards': player_stats['red_cards'],
        'Goals Conceded': player_stats['goals_conceded'],
        'Clean Sheets': player_stats['clean_sheets'],
    }

def scrape_club_players(club_url):
    """
    Download and parse player data for a given club.
    """
    html = get_html(club_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Extract club name and find player table
    club_name = str(anyascii(soup.find("h1").text.strip()))
    players_table = soup.find("table", {"class": "items"})
    players_data = []

    # Use tqdm for progress bar while processing players
    for row in tqdm(players_table.find_all("tr", {"class": ["odd", "even"]}),
                    desc=f"Processing players for {club_name}",
                    unit="player",
                    dynamic_ncols=True):
        player_data = extract_player_data(row, club_name, club_url)
        players_data.append(player_data)

    return players_data, club_name

def get_value_swos_and_stars(market_value_tm, position_swos):
    """
    Convert market value from Transfermarkt to SWOS and add stars. Returns mv_swos and stars.
    """
    if position_swos in [ 'LB', 'RB']:
        filename = 'RBLB.csv'
    elif position_swos in [ 'LW', 'RW']:
        filename = 'RWLW.csv'
    else:
        filename = f"{position_swos}.csv"

    try:
        if 'm' in market_value_tm:
            market_value_tm = int(market_value_tm.replace('€', '').replace('m', '').replace('.', '').strip()) * 10_000
        elif 'k' in market_value_tm:
            market_value_tm = int(market_value_tm.replace('€', '').replace('k', '').replace('.', '').strip()) * 1_000
        else:
            market_value_tm = int(market_value_tm.replace('€', '').replace('.', '').strip())
    except ValueError as ve:
        print(f"Error converting from market_value_tm: {ve}")
        return None, None

    filepath = os.path.join("data", filename)
    try:
        rows = pd.read_csv(filepath, delimiter=';')
        filtered_row = rows[
            (rows['mv_tm_min'] * 1_000_000 <= market_value_tm) &
            (rows['mv_tm_max'] * 1_000_000 >= market_value_tm)
        ]
        # Check if row was found
        if not filtered_row.empty:
            mv_swos = filtered_row['mv_swos'].values[0]
            stars = filtered_row['stars'].values[0]
            return mv_swos, stars

        print(f"No matching value for market_value_tm: {market_value_tm}")
        return None, None

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except pd.errors.EmptyDataError:
        print(f"Empty or invalid file: {filepath}")
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")

def get_nationality(nationality):
    """
    Get nationality from countries.csv and return SWOS nationality
    """
    filepath = os.path.join("data", "countries.csv")
    try:
        rows = pd.read_csv(filepath, delimiter=';')
        filtered_row = rows[
            (rows['nat_tm'] == nationality)
        ]
        # Check if row was found
        if not filtered_row.empty:
            nationality_swos = filtered_row['nat_swos'].values[0]
            return nationality_swos

        print(f"No matching country found: {nationality}")
        return None

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except pd.errors.EmptyDataError:
        print(f"Empty or invalid file: {filepath}")
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
    return None

def parse_arguments():
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        prog='TMScraper4SWOS',
        description="Scrape and download club and player data from Transfermarkt for use in SWOS"
    )
    parser.add_argument(
        '-u', '--clubs-url',
        help='URL of the overview page of the league. Defaults to English Premier League.',
        default='https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1',
        dest='clubs_url'
    )
    parser.add_argument(
        '-n', '--number-of-clubs',
        help='Number of clubs to download. Defaults to 1.',
        default=1,
        dest='number_of_clubs',
        type=int
    )
    return parser.parse_args()


def save_to_csv(data, league_name, country_name, club_name):
    """
    Save player data to CSV in the format:
    output/$Land/$Liganame/$Vereinsname/${Vereinsname}_player_data.csv
    """
    # Sanitize directory and file names
    league_name = league_name.replace('-', ' ').title()
    country_name = country_name.replace('-', ' ').title()
    club_name_clean = re.sub(r'[^\w\s-]', '', club_name).replace(' ', '_')

    # Define the directory structure
    output_dir = os.path.join("output", country_name, league_name, club_name_clean)

    # Create directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)

    # Save the CSV file
    csv_filename = f"{club_name_clean}_player_data.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)

    return csv_path


def scrape_transfermarkt():
    """
    Main function to scrape Transfermarkt for player data.
    """
    args = parse_arguments()
    base_url = "https://www.transfermarkt.com"
    clubs_url = args.clubs_url
    number_of_clubs = args.number_of_clubs

    # Extract league and country name from URL
    league_name = str(anyascii(clubs_url.split('/')[3]))

    print(f"==> Scraping league: {league_name.replace('-', ' ').title()}")

    html = get_html(clubs_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Find and scrape each club
    clubs_list = soup.find_all("td", {"class": "hauptlink no-border-links"})
    # Get countryname from <meta> Tag
    country_name = soup.find("meta", {"name": "keywords"}).get("content").split(',')[1]

    # Use tqdm to add a progress bar
    for club in tqdm(clubs_list[:number_of_clubs], desc="Clubs processed", unit="club", dynamic_ncols=True, leave=None):
        club_url = base_url + club.find("a").get("href")
        tqdm.write(f"==> Scraping {str(anyascii(club.text.strip()))} - {club_url}")

        try:
            club_players, club_name = scrape_club_players(club_url)
            csv_path = save_to_csv(club_players, league_name, country_name, club_name)
            tqdm.write(f"==> Data for {club_name} saved to {csv_path}")
            #tqdm.write("==> Sleeping for 2 seconds to avoid getting blocked by TM...")
            time.sleep(2)  # Short delay to avoid getting blocked
        except Exception as e:
            tqdm.write(f"Error scraping club {club.text.strip()}: {e}")


if __name__ == "__main__":
    scrape_transfermarkt()
