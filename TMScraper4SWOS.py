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

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time
import re
import argparse

def get_html(url):
    """
    Fetch HTML from Transfermarkt
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(url, headers=headers)
    return response.content

def scrape_club_players(club_url):
    """ 
    Download and parse players of a club
    """
    html = get_html(club_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Extract club name
    club_name = soup.find("h1").text.strip()
    club_schedule = club_url.replace('startseite', 'spielplan') + "/saison_id/" + str(datetime.now().year)

    # Find table with player names and values
    players_table = soup.find("table", {"class": "items"})
    players_data = []

    # Extract player rows
    for row in players_table.find_all("tr", {"class": ["odd", "even"]}):
        # Extract player name
        player_name = row.find("td", {"class": "hauptlink"}).text.strip()

        # Extract player number
        player_number = row.find("div", {"class": "rn_nummer"}).text.strip()

        # Extract player URL
        player_url = "https://transfermarkt.com" + row.find("a").get("href")

        # Extract market value
        market_value = row.find("td", {"class": "rechts hauptlink"}).text.strip()

        regex = re.compile(r'^\n')
        # Extract position
        position_tm = row.find("td", string=regex).text.strip()

        regex = re.compile(r'^\n')
        # Extract nationality
        nationality = row.find("img", {"class": "flaggenrahmen"}).get("title")

        position_tm_to_swos = {
            'Attacking Midfield': 'M',
            'Central Midfield': 'M',
            'Centre-Back': 'D',
            'Centre-Forward': 'A',
            'Defensive Midfield': 'M',
            'Goalkeeper': 'G',
            'Left Midfield': 'M',
            'Left Winger': 'LW',
            'Left-Back': 'LB',
            'Right Midfield': 'M',
            'Right Winger': 'RW',
            'Right-Back': 'RB'
        }

        players_data.append({
            'Club': club_name,
            'Club URL': club_url,
            'Schedule': club_schedule,
            'Player Number': player_number,
            'Player': player_name,
            'Player URL': player_url,
            'Nationality': nationality,
            'Position TM': position_tm,
            'Position SWOS': position_tm_to_swos[position_tm],
            'Market Value TM': market_value,
        })

    return players_data

def scrape_transfermarkt():
    """ 
    Main function - Scrape data
    """
    
    parser = argparse.ArgumentParser(
        prog='TMScraper4SWOS',
        description="Scrape and download club and player data from Transfermarkt for use in SWOS"
    )

    parser.add_argument(
        '-u', '--clubs-url',
         help='URL of the overview page of the league',
         default='https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1',
         dest='clubs_url',
         required=False
    )

    parser.add_argument(
        '-n', '--number-of-clubs',
        help='Number of clubs to download. Defaults to 1, so you do not get blocked too fast by TM',
        default=1,
        dest='number_of_clubs',
        choices=range(1, 100),
        type=int,
        required=False
    )

    args = parser.parse_args()

    base_url = "https://www.transfermarkt.com"

    clubs_url = args.clubs_url
    number_of_clubs = args.number_of_clubs

    html = get_html(clubs_url)
    soup = BeautifulSoup(html, 'html.parser')

    # Find list of clubs
    clubs_list = soup.find_all("td", {"class": "hauptlink no-border-links"})
    all_players_data = []

    for club in clubs_list[:number_of_clubs]:  # Fetch number_of_clubs clubs
        club_url = base_url + club.find("a").get("href")
        print(f"Scraping {club.text.strip()} - {club_url}")

        try:
            club_players = scrape_club_players(club_url)
            all_players_data.extend(club_players)
            time.sleep(2)  # Short sleep to avoid getting blocked by TM
        except Exception as e:
            print(f"Error scraping data from club {club.text.strip()}: {e}")

    # Save data to csv file
    df = pd.DataFrame(all_players_data)
    df.to_csv("players_data.csv", index=False)
    print("Data saved to players_data.csv")

if __name__ == "__main__":
    scrape_transfermarkt()
