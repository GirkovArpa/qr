""" main.py

Entrypoint for AutoQr

"""

import multiprocessing
import sys
import os
import PySimpleGUI as sg
from config import Config
from constants import QueueType, Roles, queue_has_roles
from lcu_api import LeagueAPI


def launch_gui(league_api):
    sg.theme('DefaultNoMoreNagging')
    layout = [
        [sg.Text(
            'Running',
            key='status',
            text_color='green',
        )],
        [sg.Checkbox(
            'Create lobby',
            key='AUTO_LOBBY',
            default=cfg.AUTO_LOBBY,
            enable_events=True,
            tooltip='Creates the game lobby for you (if you aren\'t already in one).'
        )],
        [sg.Text('Game Mode ', size=(15, 1)), sg.Combo(
            [x.name for x in QueueType],
            key='QUEUE_ID',
            default_value=cfg.QUEUE_ID.name,
            disabled=not cfg.AUTO_LOBBY,
            readonly=True,
            enable_events=True,
            size=(8, 1),
        )],
        [sg.Text("Primary Role", size=(15, 1)), sg.Combo(
            [x.name for x in Roles],
            key='PRIMARY_ROLE',
            default_value=cfg.PRIMARY_ROLE.name,
            disabled=not queue_has_roles(cfg.QUEUE_ID),
            readonly=True,
            enable_events=True,
            size=(8, 1),
        )],
        [sg.Text("Secondary Role", size=(15, 1)), sg.Combo(
            [x.name for x in Roles],
            key='SECONDARY_ROLE',
            default_value=cfg.SECONDARY_ROLE.name,
            disabled=not queue_has_roles(cfg.QUEUE_ID),
            readonly=True,
            enable_events=True,
            size=(8, 1),
        )],
        [sg.Checkbox(
            'Auto start queue',
            key='AUTO_QUEUE',
            default=cfg.AUTO_QUEUE,
            enable_events=True,
            tooltip='Starts the queue for the selected game mode automatically.'
        )],
        [sg.Checkbox(
            'Auto accept queue pop',
            key='AUTO_ACCEPT',
            default=cfg.AUTO_ACCEPT,
            enable_events=True,
        )],
        [sg.Checkbox(
            'Auto skip post-game',
            key='AUTO_SKIP_POSTGAME',
            default=cfg.AUTO_SKIP_POSTGAME,
            enable_events=True,
            tooltip='Automatically honors a random player and hits "Play Again"'
        )],
        [sg.Button('Stop', key='toggle')],
    ]
    window = sg.Window(
        title="AutoQr",
        layout=layout,
        icon=resource_path('favicon.ico'),
        finalize=True,
    )

    # Run lcu_api in the background, store its process in background_proc
    background_proc = update_state(league_api, window, background_proc=None, event='toggle', values=None)

    # GUI event loop handler
    while True:
        event, values = window.read()
        background_proc = update_state(league_api, window, background_proc, event, values)


def update_state(league_api, window, background_proc, event, values=None):
    cfg = league_api.config
    if event == 'toggle':
        background_proc = toggle_process(background_proc, league_api)
        window['status'].update(
            'Running' if background_proc else 'Not running')
        window['status'].update(
            text_color='green' if background_proc else 'red')
        window['toggle'].update('Stop' if background_proc else 'Start')
        window['AUTO_LOBBY'].update(disabled=bool(background_proc))
        window['QUEUE_ID'].update(
            disabled=not cfg.AUTO_LOBBY or bool(background_proc))
        window['PRIMARY_ROLE'].update(
            disabled=not should_display_role_selection(cfg) or bool(background_proc))
        window['SECONDARY_ROLE'].update(
            disabled=not should_display_role_selection(cfg) or bool(background_proc))
        window['AUTO_QUEUE'].update(disabled=bool(background_proc))
        window['AUTO_ACCEPT'].update(disabled=bool(background_proc))
        window['AUTO_SKIP_POSTGAME'].update(disabled=bool(background_proc))

    elif event == 'QUEUE_ID':
        cfg.QUEUE_ID = QueueType[values['QUEUE_ID']]
        window['PRIMARY_ROLE'].update(
            disabled=not should_display_role_selection(cfg) or bool(background_proc))
        window['SECONDARY_ROLE'].update(
            disabled=not should_display_role_selection(cfg) or bool(background_proc))

    # Checkboxes toggle the value
    elif event == 'AUTO_LOBBY':
        cfg.AUTO_LOBBY = not cfg.AUTO_LOBBY

        # Cannot select a queue ID if we are not creating a lobby anyways
        window['QUEUE_ID'].update(
            disabled=not cfg.AUTO_LOBBY or bool(background_proc))
        window['PRIMARY_ROLE'].update(
            disabled=not should_display_role_selection(cfg) or bool(background_proc))
        window['SECONDARY_ROLE'].update(
            disabled=not should_display_role_selection(cfg) or bool(background_proc))

    # TODO do not allow user to select the same role twice
    elif event == 'PRIMARY_ROLE':
        cfg.PRIMARY_ROLE = Roles[values['PRIMARY_ROLE']]

    elif event == 'SECONDARY_ROLE':
        cfg.SECONDARY_ROLE = Roles[values['SECONDARY_ROLE']]

    elif event == 'AUTO_QUEUE':
        cfg.AUTO_QUEUE = not cfg.AUTO_QUEUE

    elif event == 'AUTO_ACCEPT':
        cfg.AUTO_ACCEPT = not cfg.AUTO_ACCEPT

    elif event == 'AUTO_SKIP_POSTGAME':
        cfg.AUTO_SKIP_POSTGAME = not cfg.AUTO_SKIP_POSTGAME

    elif event == 'AUTO_PLAY_AGAIN':
        cfg.AUTO_PLAY_AGAIN = not cfg.AUTO_PLAY_AGAIN

    elif event == sg.WINDOW_CLOSED:
        if background_proc:
            background_proc.terminate()

    league_api.update_config(cfg)

    return background_proc

def should_display_role_selection(config: Config):
    if not config.AUTO_LOBBY:
        return False
    if not queue_has_roles(config.QUEUE_ID):
        return False
    return True


def toggle_process(proc, league_api):
    if proc is not None:
        league_api.stop_queue()
        proc.terminate()
        return None

    proc = multiprocessing.Process(target=league_api.loop, args=())
    proc.start()
    return proc


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller
    https://stackoverflow.com/a/13790741
    """
    # pylint: disable=W0703, W0212
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        # On Windows calling this function is necessary.
        multiprocessing.freeze_support()
    cfg = Config.load()
    try:
        launch_gui(LeagueAPI(cfg))
    except FileNotFoundError:
        sg.popup(
            'Failed to start',
            'Have you logged into League of Legends?',
            icon=resource_path('favicon.ico'),
            auto_close=True,
            auto_close_duration=5,
        )
