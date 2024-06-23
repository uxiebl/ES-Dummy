import click
import yaml
import logging
import xml.etree.ElementTree as ET
import requests
import platform
import re

from internetarchive import get_files
from pathlib import Path
from typing import Dict, Any
from pugixml import pugi
from contextlib import closing


# Define default configuration as a dictionary.
DEFAULT_CONFIG = {
    'Python Path': '~/.venv/bin/python3', # /usr/bin/python3
    'Python Launcher': '{python_path} %ROM%', # konsole --separate --hide-menubar --hide-tabbar --fullscreen --notransparency -e "{python_path} %ROM%"
    'Library Path': '~/Emulation/roms', # ~/Emulation/roms/thelibrary
    'ES-DE Path': '~/ES-DE',
    'Windows Systems URL': 'https://gitlab.com/es-de/emulationstation-de/-/raw/master/resources/systems/windows/es_systems.xml',
    'Linux Systems URL': 'https://gitlab.com/es-de/emulationstation-de/-/raw/master/resources/systems/linux/es_systems.xml',
    'macOS Systems URL': 'https://gitlab.com/es-de/emulationstation-de/-/raw/master/resources/systems/macos/es_systems.xml',
    'Blacklist': ['(Europe)', '(Japan)', '(France)', '(Germany)', '[BIOS', '[DLC', '[UPDATE', '(Beta', '(Rev', '(Arcade', '(Proto', '(Sample', '(Competition Cart', '(Pirate', '(Demo'],
    'ROM Extensions': ['*7z', '*zip', '*chd', '*rvz'],
    'ROM Archives': {
        'gba': ['abc123'],
        'snes': ['def456', 'ghi789']
    }
}


CONFIG_FILE = './config.yaml'


# Default configuration for the output log.
logging.basicConfig(
    filename=Path.joinpath(Path(__file__).parent, Path('./liblog.log')),
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


# Template for every new file to be generated.
OUTPUT_TEMPLATE = '''\
import zipfile
import py7zr
import logging
from pathlib import Path
from internetarchive import get_files, get_item

title = "{title}"
file_path = Path("~/Emulation/roms/{emulator}/").expanduser()
item = get_item("{identifier}")
file = item.get_file(title)
log_dir = str(Path(__file__).parent.parent)

logging.basicConfig(
    filename=log_dir + '/liblog.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

print('Initiating download request for ' + title)
logging.info('Initiating download request for ' + title)

file.download(destdir = file_path, verbose = True, retries = 3)

print('Successfully downloaded ' + title)
logging.info('Successfully downloaded ' + title)

local_filename = Path.joinpath(file_path, title)

if local_filename.is_file():
    if local_filename.suffix == '.zip': # Extract .zip file
        with zipfile.ZipFile(local_filename, 'r') as f:
            f.extractall(file_path)
        local_filename.unlink()
        print('Successfully extracted ' + title)
        logging.info('Successfully extracted ' + title)
    elif local_filename.suffix == '.7z': # Extract .7z file
        with py7zr.SevenZipFile(local_filename, mode='r') as f:
            f.extractall(path=file_path)
        local_filename.unlink()
        print('Successfully extracted ' + title)
        logging.info('Successfully extracted ' + title)
    elif Path(local_filename).parent != 'psx': # Extract from an extra subfolder
        Path(local_filename).rename(Path.joinpath(file_path, Path(local_filename).name))
        Path.rmdir(Path(local_filename).parent)
        print('Successfully moved ' + title)
        logging.info('Successfully moved ' + title)

    Path(__file__).unlink()
'''


XML_TEMPLATE = '''\
<?xml version="1.0"?>
<{tag}>
</{tag}>
'''


GAME_TEMPLATE = '''\
    <game>
        <path>{path}</path>
        <altemulator>{command}</altemulator>
    </game>
'''

SYSTEMS_TEMPLATE = '''\
    <system>
        <name>Library</name>
        <fullname>The Library</fullname>
        <path>{library_path}</path>
        <extension>.py</extension>
        <command>konsole --separate --hide-menubar --hide-tabbar --fullscreen --notransparency -e "{python_path} %ROM%" & </command>
        <theme>library</theme>
    </system>
'''


def generate_config(file_path=CONFIG_FILE, config_preset=DEFAULT_CONFIG) -> None:
    """General function for generating a configuration file to be used throughout this script."""
    parent_directory = Path(__file__).parent
    full_path = Path.joinpath(parent_directory, Path(file_path))

    with open(full_path, 'w') as file:
        yaml.dump(config_preset, file, default_flow_style=False)

    click.echo(f"Configuration file generated at: {file_path}")
    logging.info(f"Configuration file generated at: {file_path}")


def load_config(file_path=CONFIG_FILE) -> Dict[str, Any]:
    """Returns specified yaml configuration file contents in the form of a dictionary."""
    parent_directory = Path(__file__).parent
    full_path = Path.joinpath(parent_directory, Path(file_path))

    with open(full_path, 'r') as file:
        config = yaml.safe_load(file)
    return config


def generate_files(emulator: str, identifier: str) -> None:
    """Generastes files """
    click.echo(f'Initiating library population for system: {emulator}')
    logging.info(f'Initiating library population for system: {emulator}')

    # Load configuration files.
    config = load_config()

    library_path = Path(config['Library Path']).expanduser()
    es_path = Path(config['ES-DE Path']).expanduser()
    rom_extensions = config['ROM Extensions']
    blacklist = config['Blacklist']

    # Create necessary directories.
    gamelists_path = Path.joinpath(es_path, Path(f'gamelists/{emulator}'))
    gamelists_path.mkdir(parents=True, exist_ok=True)
    library_path.mkdir(parents=True, exist_ok=True)

    console_path = Path.joinpath(library_path, emulator)
    console_path.mkdir(parents=True, exist_ok=True)

    gamelist_path = Path.joinpath(gamelists_path, Path('gamelist.xml'))

    # Collect data from Internet Archive in the form of an array.
    fnames = [f.name for f in get_files(identifier, glob_pattern=rom_extensions)]

    # Iterate through obtained array entries to generate files.
    for title in fnames:
        # Filter usable file entries.
        if not any(w in title for w in blacklist):
            new_file = Path(title).stem + '.py'

            # In case there are invalid file names
            try:
                new_file = new_file.encode('utf-8').decode('utf-8') 
                rom_py = Path.joinpath(console_path, new_file)

                if not Path.exists(rom_py):
                    with open(rom_py, 'w', encoding='utf-8') as file:
                        template = OUTPUT_TEMPLATE.format(title=title, emulator=emulator, identifier=identifier)
                        file.write(template)
                        click.echo(f'Successfully generated file: \"{rom_py}\"')
                        logging.info(f'Successfully generated file: \"{rom_py}\"')
                else:
                    click.echo(f'File already exists: \"{rom_py}\"')
                    logging.error(f'File already exists: \"{rom_py}\"')
            except OSError as error:
                click.echo(f'Error creating file: {error}')
                logging.error(f'Error creating file: {error}')
            else:
                # If file was generated, add it to the gamelist.xml. This new method is currently much slower due to lack of bulk file operations. Support for multiple entries to be added.
                add_gamelist(emulator, './' + new_file,'Python')
    # Add entry to es_systems.xml.
    add_system(emulator)


def add_gamelist(emulator: str, path: str, altemulator: str) -> None:
    """Adds custom game to gamelist.xml to allow python files to be recognized and executed correctly."""
    gamelist = pugi.XMLDocument()
    game_entry = pugi.XMLDocument()

    config = load_config()

    es_path = Path(config['ES-DE Path']).expanduser()
    gamelists_path = Path.joinpath(es_path, Path(f'gamelists/{emulator}'))
    gamelists_path.mkdir(parents=True, exist_ok=True)

    gamelist_path = Path.joinpath(gamelists_path, Path('gamelist.xml'))

    if Path.exists(gamelist_path):
        gamelist.load_file(gamelist_path)
    else:
        gamelist.load_string("<gameList/>")

    game_list = gamelist.child('gameList')

    path_list = []

    # Create a list of all path entries.
    for game in game_list.children('game'):
        path_list.append(game.child('path').child_value())

    # Check if there any entries already made.
    if not path in path_list:
        game_entry.load_string(f'<game><path>{path}</path><altemulator>{altemulator}</altemulator></game>')
    
        game_list.append_copy(game_entry.child('game'))
    
        with closing(pugi.FileWriter(gamelist_path)) as writer:
            gamelist.save(writer)
    
            click.echo(f'Successfully wrote to file: \"{gamelist_path}\"')
            logging.info(f'Successfully wrote to file: \"{gamelist_path}\"')
    else:
        click.echo(f'Game entry already exists within file: \"{gamelist_path}\"')
        logging.error(f'Game entry already exists within file: \"{gamelist_path}\"')


def pull_reference() -> None:
    """Downloads the appropriate default es_systems.xml file from GitLab to be referenced in the configurable es_systems.xml file."""
    os_name = platform.system()
    config = load_config()

    if os_name == 'Windows':
        url = config['Windows Systems URL']
    elif os_name == 'Linux':
        url = config['Linux Systems URL']
    elif os_name == 'Darwin':
        url = config['macOS Systems URL']
    else:
        click.echo(f'{os_name} is not currently a supported operating system.')
        logging.error(f'{os_name} is not currently a supported operating system.')

    if url:
        file_path = Path.joinpath(Path(__file__).parent, 'es_systems.xml')
        
        try:
            response = requests.get(url)

            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    file.write(response.content)
                click.echo(f'Downloaded \"es_systems.xml\" reference file successfully: \"{file_path}\"')
                logging.info(f'Downloaded \"es_systems.xml\" reference file successfully: \"{file_path}\"')
            else:
                click.echo(f'Failed to download file. [STATUS_CODE: {response.status_code}]')
                logging.error(f'Failed to download file. [STATUS_CODE: {response.status_code}]')
        except requests.exceptions.RequestException as error:
            click.echo(f"Error downloading file: {error}")
            logging.error(f"Error downloading file: {error}")


def add_system(emulator: str) -> None:
    """Adds custom system to es_systems.xml by referencing default es_systems.xml file to allow python files to be recognized and executed correctly."""
    default_systems = pugi.XMLDocument()
    default_systems_path = Path.joinpath(Path(__file__).parent, 'es_systems.xml')

    # Retrieve new default es_systems.xml file if one was not already downloaded locally.
    if not Path.exists(default_systems_path):
        pull_reference()
    
    default_systems.load_file(default_systems_path)
    default_system_list = default_systems.child('systemList')

    config = load_config()

    systems = pugi.XMLDocument()
    es_path = Path(config['ES-DE Path']).expanduser()
    systems_path = Path.joinpath(es_path, Path('custom_systems/es_systems.xml'))

    if Path.exists(systems_path):
        systems.load_file(systems_path)
    else:
        systems.load_string("<systemList/>")
    
    system_list = systems.child('systemList')

    # Path to python3 to launch specified %ROM% argument, now expected to be within a virtual environment.
    python_path = Path(config['Python Path']).expanduser()

    # Allows us to launch python through a terminal so we can visualize progress.
    python_launcher = str(Path(config['Python Launcher'].format(python_path=python_path)))
    #print(python_launcher)

    # Iterate through the default systemList node to find the specified child node and create a new child to append to the new systemList node.
    for system in default_system_list.children('system'):
        name = system.child('name')
        if name:
            name_value = name.child_value().strip()
    
            if name_value == emulator:
                # Modify extension node to include python extensions.
                extension = system.child('extension')
                extension_value = system.child('extension').child_value()
                extension.first_child().set_value(f'{extension_value} .py .PY')
    
                # Copy first command node and insert at the top of the system node.
                reference_command = system.children('command')[0]
                command = system.prepend_copy(reference_command)
    
                # Move copied command node after the last command node.
                last_command = system.children('command')[-1]
                system.insert_move_after(command, last_command)
                
                # Format copied command node to properly execute python scripts.
                command.first_attribute().set_value('Python')
                command.first_child().set_value(python_launcher)
    
                # Copy and append default system node to new systemList node.
                system_list.append_copy(system)
    
                #if not system in system_list.children('system'):
                    #new_system = system_list.append_copy(system)
                    #print(new_system)
                #else:
                    #print(f'\"system\" child node already exists within \"systemList\" for file: {systems_path}')
                break
    with closing(pugi.FileWriter(systems_path)) as writer:
        systems.save(writer)

        click.echo(f'Successfully wrote to file: \"{systems_path}\"')
        logging.info(f'Successfully wrote to file: \"{systems_path}\"')


@click.group()
def cli():
    """Program for populating emulator frontends with dummy ROM files embedded with a python script for downloading and extracting actual ROM files in their place.

    Intended for downloading ROM titles directly through EmulationStation."""
    pass


@cli.command()
@click.argument('emulator')
@click.argument('identifier')
def populate(emulator: str, identifier: str):
    """Populates specified emulator system with dummy ROM files pulled from specified Internet Archive identifier"""
    generate_files(emulator, identifier)


@cli.command()
def populate_all():
    """Populates all configured emulator systems with dummy ROM files pulled from specified Internet Archive identifier"""
    click.echo('Populating ROM directories with all available ROM titles')
    
    config = load_config()

    for system, archive in config['ROM Archives'].items():
        for subarchive in archive:
            generate_files(system, subarchive)


@cli.command()
def clean():
    """Deleted all dummy ROM files previously populated within specified emulator ROM directories."""
    config = load_config()

    library_path = Path(config['Library Path']).expanduser()
    list = Path(library_path).glob('**/*')

    for item in list:
        if item.suffix == '.py':
            item.unlink()
            click.echo(f'Deleted file: \"{item}\"')
            logging.info(f'Deleted file: \"{item}\"')


@cli.command()
def add_library():
    """Adds python path to the custom EmulationStation configuration file so that dummy ROM files can be launched correctly"""
    config = load_config()

    python_path = Path(config['Python Path']).expanduser()
    library_path = Path(config['Library Path']).expanduser()
    es_path = Path(config['ES-DE Path']).expanduser()
    systems_path = Path.joinpath(es_path, Path('custom_systems/es_systems.xml'))

    library_content = SYSTEMS_TEMPLATE.format(library_path=library_path, python_path=python_path)
    
    insert_xml(systems_path, 'systemList', library_content)


@cli.command()
def archives():
    """Print configuration file dictionary contents to test the capabilities of YAML configuration files."""
    config = load_config()

    for system, archive in config['ROM Archives'].items():
        for subarchive in archive:
            click.echo(f'Emulator: {system}, Identifier: {subarchive}')


@cli.command()
@click.argument('emulator')
@click.argument('identifier')
def gamelist():
    """Write to gamelist.xml"""
    #config = load_config()
    #es_path = Path(config['ES-DE Path']).expanduser()
    #gamelist_path = Path.joinpath(es_path, Path('gamelists/gc/gamelist.xml'))
    
    #content = GAME_TEMPLATE.format(path='', command='python %ROM%')
    #insert_xml(gamelist_path, 'gameList', content)

    add_gamelist('gba', 'test.py')


@cli.command()
def update_resources():
    """Updates default es_systems.xml resource with the latest version. If there are any significant changes to this file, it is possible that a system may no longer launch correctly."""
    reference_path = Path.joinpath(Path(__file__).parent, 'es_systems.xml')

    # Deletes old default es_systems.xml file if none was already downloaded locally.
    if Path.exists(reference_path):
        reference_path.unlink()
        click.echo(f'Deleted existing \"es_systems.xml\" file successfully: \"{reference_path}\"')
        logging.info(f'Deleted existing \"es_systems.xml\" file successfully: \"{reference_path}\"')

    pull_reference()


@cli.command()
@click.argument('emulator')
def populate_system(emulator: str):
    """Command for manually adding python support for a given system."""
    add_system(emulator)


if __name__ == '__main__':
    config_file = Path.joinpath(Path(__file__).parent, 'config.yaml')

    if not Path.exists(config_file):
        generate_config(config_file)

    cli()