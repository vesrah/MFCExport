#!/bin/python
# Joseph Brasch / jbrasch@gmail.com / 8/2019
import csv
import math
import requests
import sys
from bs4 import BeautifulSoup

PROFILE_URL = "https://myfigurecollection.net/users.v4.php"
PROFILE_QUERYSTRING = {
    "mode": "view",
    "username": "",
    "tab": "collection",
    "status": 2,
    "output": 2,
    "current": "keywords",
    "rootId": 0,
    "categoryId": -1,
    "sort": "category",
    "order": "asc",
    "page": 1
}

API_URL = "https://myfigurecollection.net/api_v2.php"
API_QUERYSTRING = {
    "type": "json",
    "access": "read",
    "object": "items",
    "id": 0
}

# Get the data for the figures from the MFC JSON API
def get_figure_data(figures):
    print("Getting data for " + str(len(figures)) + " figures...")
    figures_with_data = []

    for (i, figure) in enumerate(figures):
        API_QUERYSTRING.update({ "id": figure[0] })
        api_response = requests.get(API_URL, API_QUERYSTRING).json()["items"]

        if (int(api_response["count"]) > 1):
            print("API returned more than one item for item id " + figure["figure_id"] + ", this is kind of weird.  Skipping it")
            return

        figure_data = api_response["item"]
        figure_detail_url = "https://myfigurecollection.net/item/" + str(figure[0])
        figure_release_date = str(figure_data["release_date"])

        # Sometimes the figures are given a 00 day of the month,
        # set it to the first of the month for Google Sheets date formatting
        if (figure_release_date.endswith("-00")):
            figure_release_date = figure_release_date.replace("-00", "-01")

        # Also get rid of another weird API thing
        figure_release_date = figure_release_date.replace("{}", "")

        figures_with_data = figures_with_data + [(
            figure[0],
            figure_data["name"],
            int(figure_data["price"]),
            figure_release_date,
            figure[1],
            figure_detail_url,
            figure_data["thumbnail"],
            figure_data["full"],
        )]

    print("Retrieved data for " + str(len(figures_with_data)) + " figures")
    return figures_with_data

# Scrape the figure ids and owned count from a profile page
def scrape_figures_from_profile_page(page_soup):
    figures = []
    figure_elements = page_soup.find_all(class_="item-icon")

    for figure in figure_elements:
        figure_anchor_element = figure.find("a")
        figure_times_collected_element = figure.find(class_="item-times-collected")

        figure_id = int(figure_anchor_element["href"].split("/")[-1])
        figure_times_collected = 1

        if (figure_times_collected_element):
            figure_times_collected = int(figure_times_collected_element.text.replace("×", ""))

        figures = figures + [(figure_id, figure_times_collected)]

    return figures

# Scrape all of the figures for the profile
def get_figures(first_page_soup, page_count):
    print("Getting figures from page 1 of " + str(page_count))
    figure_list = scrape_figures_from_profile_page(first_page_soup)

    for page in range(2, page_count + 1):
        print("Getting figures from page " + str(page) + " of " + str(page_count))
        PROFILE_QUERYSTRING.update({ "page": page })
        page_raw_data = requests.get(PROFILE_URL, PROFILE_QUERYSTRING).text
        page_soup = BeautifulSoup(page_raw_data, "html.parser")
        figure_list = figure_list + scrape_figures_from_profile_page(page_soup)

    return figure_list

# Determine the number of pages we will need to scrape
def get_page_count(profile_soup):
    page_count_text = profile_soup.find(class_="listing-count-value").text
    figure_count = int(page_count_text.split()[0].replace(",", ""))
    return math.ceil(figure_count / 90)

# Write a CSV to the filesystem
def write_csv(figure_list):
    filename = "mfcexport-" + PROFILE_QUERYSTRING["username"].replace(" ", "_") + ".csv"
    print("Writing " + str(len(figure_list)) + " figures to " + filename + "...")

    # Sort by Figure ID
    figure_list = sorted(figure_list, key=lambda f: f[0])

    with open(filename, "w", newline="", encoding="utf-8") as output:
        file_writer = csv.writer(output)
        file_writer.writerow([
            "ID",
            "Name",
            "Price (JPY)",
            "Release Date",
            "Owned Count",
            "Detail URL",
            "Thumbnail URL",
            "Large Image URL"
        ])
        file_writer.writerows(figure_list)

    print("MFC data export complete")

# Get the figure data
def get_figure_list():
    profile_raw_data = requests.get(PROFILE_URL, PROFILE_QUERYSTRING).text
    profile_soup = BeautifulSoup(profile_raw_data, "html.parser")
    page_count = get_page_count(profile_soup)

    if (page_count == 0):
        print("No pages returned, please check your username")
        exit()

    figures = get_figures(profile_soup, page_count)
    write_csv(get_figure_data(figures))

def main():
    if (len(sys.argv) != 2):
        print("Usage: python mfcExport.py username")
    else:
        PROFILE_QUERYSTRING.update({ "username": sys.argv[1]})
        print("Retrieving figure data for " + PROFILE_QUERYSTRING["username"] + "...")
        get_figure_list()

main()