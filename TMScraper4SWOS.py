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


def extract_player_data(row, club_name, club_url):
    """
    Extract relevant player data from a table row.
    """
    player_name = row.find("td", {"class": "hauptlink"}).text.strip()
    player_number = row.find("div", {"class": "rn_nummer"}).text.strip()
    player_url = "https://transfermarkt.com" + row.find("a").get("href")
    market_value = row.find("td", {"class": "rechts hauptlink"}).text.strip()

    # Extract position and nationality
    regex = re.compile(r'^\n')
    position_tm = row.find("td", string=regex).text.strip()
    nationality = row.find("img", {"class": "flaggenrahmen"}).get("title")

    # Convert position from Transfermarkt to SWOS format
    position_tm_to_swos = {
        'Attacking Midfield': 'M', 'Central Midfield': 'M', 'Centre-Back': 'D',
        'Centre-Forward': 'A', 'Defensive Midfield': 'M', 'Goalkeeper': 'G',
        'Left Midfield': 'M', 'Left Winger': 'LW', 'Left-Back': 'LB',
        'Right Midfield': 'M', 'Right Winger': 'RW', 'Right-Back': 'RB'
    }

    return {
        'Club': club_name,
        'Club URL': club_url,
        'Schedule': f"{club_url.replace('startseite', 'spielplan')}/saison_id/{datetime.now().year}",
        'Player Number': player_number,
        'Player': player_name,
        'Player URL': player_url,
        'Nationality': nationality,
        'Position TM': position_tm,
        'Position SWOS': position_tm_to_swos.get(position_tm, 'Unknown'),
        'Market Value TM': market_value,
    }


def scrape_club_players(club_url):
    """
    Download and parse player data for a given club.
    """
    html = get_html(club_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Extract club name and find player table
    club_name = soup.find("h1").text.strip()
    players_table = soup.find("table", {"class": "items"})
    players_data = []

    # Extract player data for each row
    for row in players_table.find_all("tr", {"class": ["odd", "even"]}):
        player_data = extract_player_data(row, club_name, club_url)
        players_data.append(player_data)

    return players_data, club_name


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
        help='URL of the overview page of the league',
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
    #print(f"Data for {club_name} saved to {csv_path}")


def scrape_transfermarkt():
    """
    Main function to scrape Transfermarkt for player data.
    """
    args = parse_arguments()
    base_url = "https://www.transfermarkt.com"
    clubs_url = args.clubs_url
    number_of_clubs = args.number_of_clubs

    # Extract league and country name from URL
    league_name = clubs_url.split('/')[3]

    print(f"==> Scraping league: {league_name.replace('-', ' ').title()}")

    html = get_html(clubs_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Find and scrape each club
    clubs_list = soup.find_all("td", {"class": "hauptlink no-border-links"})
    # Get countryname from <meta> Tag
    country_name = soup.find("meta", {"name": "keywords"}).get("content").split(',')[1]

    # Use tqdm to add a progress bar
    for club in tqdm(clubs_list[:number_of_clubs], desc="Clubs Processed", unit="club", dynamic_ncols=True):
        club_url = base_url + club.find("a").get("href")
        tqdm.write(f"==> Scraping {club.text.strip()} - {club_url}")

        try:
            club_players, club_name = scrape_club_players(club_url)
            csv_path = save_to_csv(club_players, league_name, country_name, club_name)
            tqdm.write(f"==> Data for {club_name} saved to {csv_path}")
            time.sleep(2)  # Short delay to avoid getting blocked
        except Exception as e:
            tqdm.write(f"Error scraping club {club.text.strip()}: {e}")


if __name__ == "__main__":
    scrape_transfermarkt()
