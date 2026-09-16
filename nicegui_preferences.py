"""Versioned browser preferences for Folio: last valid settings and profiles.

This store identifies a browser, not an authenticated account. It never holds a
generated PDF, only the validated configuration exports the user already owns.
A corrupt or outdated store falls back to the defaults with a message instead
of blocking the workspace; importing a JSON file always stays available.
"""

import uuid

from nicegui_service import parse_config


VERSION = 1
STORAGE_KEY = 'folio_preferences'
NAME_LIMIT = 48
PROFILE_LIMIT = 20
MODES = ('dated', 'undated')
CORRUPT_MESSAGE = ('Réglages enregistrés illisibles : Folio repart de ses valeurs par '
                   'défaut. Vos fichiers JSON restent importables.')
PARTIAL_MESSAGE = ('Certains réglages enregistrés ont été ignorés parce qu’ils n’étaient '
                   'plus valides. Les autres ont été restaurés.')


def empty():
    return {'version': VERSION, 'active_mode': 'dated',
            'last_valid': {mode: None for mode in MODES}, 'profiles': []}


def valid_config(mode, payload):
    """The stored export, once it still builds a configuration; None otherwise."""
    if mode not in MODES or not isinstance(payload, dict):
        return None
    try:
        return parse_config(mode, payload).to_dict()
    except (ValueError, TypeError):
        return None


def clean_name(name):
    text = ' '.join(str(name).split()) if isinstance(name, str) else ''
    if not text or len(text) > NAME_LIMIT:
        raise ValueError(f'Le nom du profil doit contenir de 1 à {NAME_LIMIT} caractères.')
    return text


def _profile(raw):
    if not isinstance(raw, dict):
        return None
    mode = raw.get('mode')
    config = valid_config(mode, raw.get('config'))
    identifier = raw.get('id')
    if config is None or not isinstance(identifier, str) or not identifier:
        return None
    try:
        name = clean_name(raw.get('name'))
    except ValueError:
        return None
    return {'id': identifier, 'name': name, 'mode': mode, 'config': config}


def load(raw):
    """Return (preferences, message); the message is empty when nothing was lost."""
    if raw in (None, {}):
        return empty(), ''
    if not isinstance(raw, dict) or raw.get('version') != VERSION:
        return empty(), CORRUPT_MESSAGE
    preferences = empty()
    dropped = False
    if raw.get('active_mode') in MODES:
        preferences['active_mode'] = raw['active_mode']
    stored = raw.get('last_valid')
    for mode in MODES:
        candidate = stored.get(mode) if isinstance(stored, dict) else None
        if candidate is not None:
            config = valid_config(mode, candidate)
            dropped = dropped or config is None
            preferences['last_valid'][mode] = config
    profiles, seen = [], set()
    for entry in raw.get('profiles') if isinstance(raw.get('profiles'), list) else []:
        profile = _profile(entry)
        if profile is None or profile['id'] in seen:
            dropped = True
            continue
        seen.add(profile['id'])
        profiles.append(profile)
    preferences['profiles'] = profiles[:PROFILE_LIMIT]
    dropped = dropped or len(profiles) > PROFILE_LIMIT
    return preferences, PARTIAL_MESSAGE if dropped else ''


def remember(preferences, mode, config):
    """Store one validated configuration as the starting point of its mode."""
    if valid_config(mode, config) is None:
        raise ValueError('Seule une configuration valide peut être enregistrée.')
    updated = dict(preferences)
    updated['active_mode'] = mode
    updated['last_valid'] = dict(preferences['last_valid'], **{mode: config})
    return updated


def find(preferences, identifier):
    for profile in preferences['profiles']:
        if profile['id'] == identifier:
            return profile
    return None


def save_profile(preferences, name, mode, config, identifier=None):
    """Create or replace a profile. Profiles are addressed by UUID, never by name."""
    if valid_config(mode, config) is None:
        raise ValueError('Seule une configuration valide peut devenir un profil.')
    profile = {'id': identifier or str(uuid.uuid4()), 'name': clean_name(name),
               'mode': mode, 'config': config}
    profiles = [dict(entry) for entry in preferences['profiles']]
    for index, entry in enumerate(profiles):
        if entry['id'] == profile['id']:
            profiles[index] = profile
            break
    else:
        if len(profiles) >= PROFILE_LIMIT:
            raise ValueError(f'Folio conserve au maximum {PROFILE_LIMIT} profils. '
                             'Supprimez-en un avant d’en ajouter un autre.')
        profiles.append(profile)
    return dict(preferences, profiles=profiles), profile['id']


def rename_profile(preferences, identifier, name):
    if find(preferences, identifier) is None:
        raise ValueError('Ce profil n’existe plus.')
    profiles = [dict(entry, name=clean_name(name)) if entry['id'] == identifier else dict(entry)
                for entry in preferences['profiles']]
    return dict(preferences, profiles=profiles)


def delete_profile(preferences, identifier):
    if find(preferences, identifier) is None:
        raise ValueError('Ce profil n’existe plus.')
    return dict(preferences, profiles=[dict(entry) for entry in preferences['profiles']
                                       if entry['id'] != identifier])
