# 29.06.24

import os
import sys
import logging
from urllib.parse import urlparse


# Internal utilities
from Src.Util.console import console, msg
from Src.Util.message import start_message
from Src.Util.os import create_folder, can_create_file
from Src.Util.table import TVShowManager
from Src.Lib.Downloader import MP4_downloader
from ..Template import manage_selection, map_episode_title, validate_selection, validate_episode_selection


# Logic class
from .Core.Player.episode_scraper import ApiManager
from .Core.Player.driveleech import DownloadAutomation
from ..Template.Class.SearchType import MediaItem
from .film import download_film


# Variable
from .costant import ROOT_PATH, SITE_NAME, SERIES_FOLDER
table_show_manager = TVShowManager()



def download_video(api_manager: ApiManager, index_season_selected: int, index_episode_selected: int) -> None:
    """
    Download a single episode video.

    Parameters:
        - tv_name (str): Name of the TV series.
        - index_season_selected (int): Index of the selected season.
        - index_episode_selected (int): Index of the selected episode.
    """

    start_message()

    # Get info about episode
    obj_episode = api_manager.obj_episode_manager.episodes[index_episode_selected - 1]
    tv_name = api_manager.obj_season_manager.seasons[index_season_selected - 1].name
    console.print(f"[yellow]Download: [red]{index_season_selected}:{index_episode_selected} {obj_episode.title}")
    print()

    # Define filename and path for the downloaded video
    mp4_name = f"{map_episode_title(tv_name, index_season_selected, index_episode_selected, obj_episode.title)}.mp4"
    mp4_path = os.path.join(ROOT_PATH, SITE_NAME, SERIES_FOLDER,  tv_name, f"S{index_season_selected}")

    # Check if can create file output
    create_folder(mp4_path)                                                                    
    if not can_create_file(mp4_name):  
        logging.error("Invalid mp4 name.")
        sys.exit(0)
    
    # Parse start page url
    start_message()
    downloder_vario = DownloadAutomation(obj_episode.url)
    downloder_vario.run()
    downloder_vario.quit()

    # Parse mp4 link
    mp4_final_url = downloder_vario.mp4_link
    parsed_url = urlparse(mp4_final_url)

    MP4_downloader(
        url = mp4_final_url, 
        path = os.path.join(mp4_path, mp4_name),
        referer = f"{parsed_url.scheme}://{parsed_url.netloc}/",
    )


def download_episode(api_manager: ApiManager, index_season_selected: int, download_all: bool = False) -> None:
    """
    Download all episodes of a season.

    Parameters:
        - tv_name (str): Name of the TV series.
        - index_season_selected (int): Index of the selected season.
        - download_all (bool): Download all seasons episodes
    """

    # Clean memory of all episodes and get the number of the season (some dont follow rule of [1,2,3,4,5] but [1,2,3,145,5,6,7]).
    api_manager.obj_episode_manager.clear()
    season_name = api_manager.obj_season_manager.seasons[index_season_selected-1].name

    # Collect all best episode
    start_message()
    api_manager.collect_episode(season_name)
    episodes_count = api_manager.obj_episode_manager.get_length()

    if download_all:

        # Download all episodes without asking
        for i_episode in range(1, episodes_count + 1):
            download_video(api_manager, index_season_selected, i_episode)
        console.print(f"\n[red]End downloaded [yellow]season: [red]{index_season_selected}.")

    else:

        # Display episodes list and manage user selection
        last_command = display_episodes_list()
        list_episode_select = manage_selection(last_command, episodes_count)

        try:
            list_episode_select = validate_episode_selection(list_episode_select, episodes_count)
        except ValueError as e:
            console.print(f"[red]{str(e)}")
            return

        # Download selected episodes
        for i_episode in list_episode_select:
            download_video(api_manager, index_season_selected, i_episode)


def download_serie(media: MediaItem):
    """
    Downloads a media title using its API manager and WebAutomation driver.

    Parameters:
        media (MediaItem): The media item to be downloaded.
    """

    start_message()
    
    # Initialize the API manager with the media and driver
    api_manager = ApiManager(media.url)

    # Collect information about seasons
    api_manager.collect_season()
    seasons_count = api_manager.obj_season_manager.get_length()

    if seasons_count > 0:

        # Prompt user for season selection and download episodes
        console.print(f"\n[green]Seasons found: [red]{seasons_count}")
        index_season_selected = msg.ask(
            "\n[cyan]Insert season number [yellow](e.g., 1), [red]* [cyan]to download all seasons, "
            "[yellow](e.g., 1-2) [cyan]for a range of seasons, or [yellow](e.g., 3-*) [cyan]to download from a specific season to the end"
        )
        
        # Manage and validate the selection
        list_season_select = manage_selection(index_season_selected, seasons_count)

        try:
            list_season_select = validate_selection(list_season_select, seasons_count)
        except ValueError as e:
            console.print(f"[red]{str(e)}")
            return

        # Loop through the selected seasons and download episodes
        for i_season in list_season_select:
            if len(list_season_select) > 1 or index_season_selected == "*":

                # Download all episodes if multiple seasons are selected or if '*' is used
                download_episode(api_manager, i_season, download_all=True)
            else:

                # Otherwise, let the user select specific episodes for the single season
                download_episode(api_manager, i_season, download_all=False)

    else:

        # If not seasons find is a film 
        obj_film = api_manager.episode_scraper.info_site[0]
        download_film(obj_film.get('name'), obj_film.get('url'))


def display_episodes_list(api_manager: ApiManager) -> str:
    """
    Display episodes list and handle user input.

    Returns:
        last_command (str): Last command entered by the user.
    """

    # Set up table for displaying episodes
    table_show_manager.set_slice_end(10)

    # Add columns to the table
    column_info = {
        "Index": {'color': 'red'},
        "Name": {'color': 'magenta'},
    }
    table_show_manager.add_column(column_info)

    # Populate the table with episodes information
    for i, media in enumerate(api_manager.obj_episode_manager.episodes):
        table_show_manager.add_tv_show({
            'Index': str(i),
            'Name': media.title
        })

    # Run the table and handle user input
    last_command = table_show_manager.run()

    if last_command == "q":
        console.print("\n[red]Quit [white]...")
        sys.exit(0)

    return last_command
