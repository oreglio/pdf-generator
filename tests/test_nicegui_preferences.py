import json
import unittest
from dataclasses import replace

import nicegui_preferences as preferences
from dated_planner_config import DatedPlannerConfig
from planner_config import PlannerConfig


DATED = DatedPlannerConfig(base=PlannerConfig(list_count=1, tasks_per_list=2),
                           start_date='2026-09-16', months=6).to_dict()
UNDATED = PlannerConfig(days=12, title='Mon carnet').to_dict()


class LoadingTests(unittest.TestCase):
    def test_a_fresh_browser_starts_from_the_defaults_without_a_message(self):
        for raw in (None, {}):
            with self.subTest(raw=raw):
                state, message = preferences.load(raw)
                self.assertEqual(message, '')
                self.assertEqual(state, preferences.empty())
                self.assertEqual(state['version'], preferences.VERSION)
                self.assertIsNone(state['last_valid']['dated'])

    def test_corrupt_or_outdated_storage_falls_back_with_a_message(self):
        for raw in ([], 'text', 42, {'version': 99}, {'version': None},
                    {'last_valid': {'dated': UNDATED}}):
            with self.subTest(raw=raw):
                state, message = preferences.load(raw)
                self.assertEqual(state, preferences.empty())
                self.assertEqual(message, preferences.CORRUPT_MESSAGE)

    def test_both_modes_are_restored_separately(self):
        state = preferences.remember(preferences.empty(), 'dated', DATED)
        state = preferences.remember(state, 'undated', UNDATED)
        restored, message = preferences.load(json.loads(json.dumps(state)))
        self.assertEqual(message, '')
        self.assertEqual(restored['active_mode'], 'undated')
        self.assertEqual(restored['last_valid']['dated'], DATED)
        self.assertEqual(restored['last_valid']['undated'], UNDATED)
        self.assertEqual(DatedPlannerConfig.from_dict(restored['last_valid']['dated']).months, 6)

    def test_invalid_entries_are_dropped_and_the_rest_survives(self):
        state = preferences.remember(preferences.empty(), 'undated', UNDATED)
        state['last_valid']['dated'] = {'months': 99}
        state['profiles'] = [
            {'id': 'a', 'name': 'Travail', 'mode': 'undated', 'config': UNDATED},
            {'id': 'b', 'name': 'Cassé', 'mode': 'undated', 'config': {'days': 0}},
            {'id': 'a', 'name': 'Doublon', 'mode': 'undated', 'config': UNDATED},
            {'id': '', 'name': 'Sans identifiant', 'mode': 'undated', 'config': UNDATED},
            {'id': 'c', 'name': '', 'mode': 'undated', 'config': UNDATED},
            {'id': 'd', 'name': 'Mode inconnu', 'mode': 'other', 'config': UNDATED},
            'not a profile',
        ]
        restored, message = preferences.load(state)
        self.assertEqual(message, preferences.PARTIAL_MESSAGE)
        self.assertIsNone(restored['last_valid']['dated'])
        self.assertEqual(restored['last_valid']['undated'], UNDATED)
        self.assertEqual([profile['id'] for profile in restored['profiles']], ['a'])

    def test_an_old_export_without_device_fields_is_still_restored(self):
        legacy = {key: value for key, value in UNDATED.items()
                  if key not in ('device', 'density', 'custom_width_mm', 'custom_height_mm')}
        state = {'version': 1, 'active_mode': 'undated',
                 'last_valid': {'dated': None, 'undated': legacy}, 'profiles': []}
        restored, message = preferences.load(state)
        self.assertEqual(message, '')
        self.assertEqual(restored['last_valid']['undated']['device'], 'viwoods-aipaper')
        self.assertEqual(restored['last_valid']['undated']['density'], 'standard')

    def test_two_browsers_never_share_a_dictionary(self):
        first = preferences.empty()
        second = preferences.empty()
        first = preferences.remember(first, 'undated', UNDATED)
        first, _ = preferences.save_profile(first, 'Travail', 'undated', UNDATED)
        self.assertIsNone(second['last_valid']['undated'])
        self.assertEqual(second['profiles'], [])
        self.assertEqual(preferences.empty()['profiles'], [])


class ProfileTests(unittest.TestCase):
    def test_profiles_are_addressed_by_uuid_not_by_name(self):
        state, first = preferences.save_profile(preferences.empty(), 'Travail', 'dated', DATED)
        state, second = preferences.save_profile(state, 'Travail', 'undated', UNDATED)
        self.assertNotEqual(first, second)
        self.assertEqual(len(state['profiles']), 2)
        self.assertEqual(preferences.find(state, first)['mode'], 'dated')
        self.assertEqual(preferences.find(state, second)['config'], UNDATED)
        self.assertIsNone(preferences.find(state, 'unknown'))

    def test_saving_over_an_existing_identifier_replaces_it(self):
        state, identifier = preferences.save_profile(preferences.empty(), 'Travail', 'dated', DATED)
        changed = replace(DatedPlannerConfig.from_dict(DATED), months=12).to_dict()
        state, same = preferences.save_profile(state, 'Travail · trimestre', 'dated',
                                               changed, identifier)
        self.assertEqual(same, identifier)
        self.assertEqual(len(state['profiles']), 1)
        self.assertEqual(preferences.find(state, identifier)['name'], 'Travail · trimestre')
        self.assertEqual(preferences.find(state, identifier)['config']['months'], 12)

    def test_names_are_trimmed_limited_and_never_empty(self):
        state, identifier = preferences.save_profile(preferences.empty(),
                                                     '  Travail   trimestre  ', 'dated', DATED)
        self.assertEqual(preferences.find(state, identifier)['name'], 'Travail trimestre')
        for name in ('', '   ', '\n', 'x' * 49, None, 12):
            with self.subTest(name=name), self.assertRaises(ValueError):
                preferences.save_profile(state, name, 'dated', DATED)
        renamed = preferences.rename_profile(state, identifier, 'Personnel')
        self.assertEqual(preferences.find(renamed, identifier)['name'], 'Personnel')
        self.assertEqual(preferences.find(state, identifier)['name'], 'Travail trimestre')

    def test_invalid_configurations_never_become_profiles_or_defaults(self):
        for mode, config in (('undated', {'days': 0}), ('dated', {'months': 0}),
                             ('other', UNDATED), ('undated', 'text')):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                preferences.save_profile(preferences.empty(), 'Essai', mode, config)
            with self.subTest(mode=mode, action='remember'), self.assertRaises(ValueError):
                preferences.remember(preferences.empty(), mode, config)

    def test_deleting_and_renaming_an_unknown_profile_is_refused(self):
        state, identifier = preferences.save_profile(preferences.empty(), 'Travail', 'dated', DATED)
        for action in (preferences.delete_profile,):
            with self.assertRaises(ValueError):
                action(state, 'unknown')
        with self.assertRaises(ValueError):
            preferences.rename_profile(state, 'unknown', 'Autre')
        emptied = preferences.delete_profile(state, identifier)
        self.assertEqual(emptied['profiles'], [])
        self.assertEqual(len(state['profiles']), 1)

    def test_the_number_of_profiles_stays_bounded(self):
        state = preferences.empty()
        for number in range(preferences.PROFILE_LIMIT):
            state, _ = preferences.save_profile(state, f'Profil {number}', 'undated', UNDATED)
        with self.assertRaises(ValueError):
            preferences.save_profile(state, 'Un de trop', 'undated', UNDATED)
        self.assertEqual(len(preferences.load(state)[0]['profiles']), preferences.PROFILE_LIMIT)

    def test_a_stored_profile_survives_a_json_round_trip(self):
        state, identifier = preferences.save_profile(preferences.empty(), 'Travail', 'dated', DATED)
        restored, message = preferences.load(json.loads(json.dumps(state)))
        self.assertEqual(message, '')
        profile = preferences.find(restored, identifier)
        self.assertEqual(DatedPlannerConfig.from_dict(profile['config']),
                         DatedPlannerConfig.from_dict(DATED))


if __name__ == '__main__':
    unittest.main()
