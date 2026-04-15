"""
Django management command to extract gender and age data from existing accident records.
This command parses the victim_details and suspect_details text fields to extract
demographic information and populate the new gender/age fields.

Usage:
    python manage.py extract_gender_data
    python manage.py extract_gender_data --dry-run  # Preview without saving
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accidents.models import Accident
import re
import random


class Command(BaseCommand):
    help = 'Extract gender and age data from existing accident records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database',
        )
        parser.add_argument(
            '--fill-unknown',
            action='store_true',
            help='Fill UNKNOWN gender records using Philippine traffic accident statistics '
                 '(PNP/MMDA/WHO data: ~87%% male, ~13%% female drivers; ~72%% male, ~28%% female victims)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('GENDER & AGE DATA EXTRACTION'))
        self.stdout.write(self.style.WARNING('=' * 80))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n[DRY RUN MODE] - No changes will be saved\n'))

        # Get all accidents
        accidents = Accident.objects.all()
        total_count = accidents.count()

        self.stdout.write(f'\nTotal accidents to process: {total_count:,}\n')

        # Statistics
        stats = {
            'total_processed': 0,
            'driver_gender_extracted': 0,
            'victim_gender_extracted': 0,
            'driver_age_extracted': 0,
            'victim_age_extracted': 0,
            'male_drivers': 0,
            'female_drivers': 0,
            'male_victims': 0,
            'female_victims': 0,
        }

        # Process in batches for better performance
        batch_size = 1000
        accidents_to_update = []

        for idx, accident in enumerate(accidents.iterator(), 1):
            # Extract driver/suspect data
            driver_gender, driver_age = self.extract_person_data(accident.suspect_details)

            # Extract victim data
            victim_gender, victim_age = self.extract_person_data(accident.victim_details)

            # Update accident object
            updated = False

            if driver_gender and driver_gender != 'UNKNOWN':
                accident.driver_gender = driver_gender
                stats['driver_gender_extracted'] += 1
                if driver_gender == 'MALE':
                    stats['male_drivers'] += 1
                else:
                    stats['female_drivers'] += 1
                updated = True

            if driver_age is not None:
                accident.driver_age = driver_age
                stats['driver_age_extracted'] += 1
                updated = True

            if victim_gender and victim_gender != 'UNKNOWN':
                accident.victim_gender = victim_gender
                stats['victim_gender_extracted'] += 1
                if victim_gender == 'MALE':
                    stats['male_victims'] += 1
                else:
                    stats['female_victims'] += 1
                updated = True

            if victim_age is not None:
                accident.victim_age = victim_age
                stats['victim_age_extracted'] += 1
                updated = True

            if updated:
                accidents_to_update.append(accident)
                stats['total_processed'] += 1

            # Save in batches
            if len(accidents_to_update) >= batch_size:
                if not dry_run:
                    with transaction.atomic():
                        Accident.objects.bulk_update(
                            accidents_to_update,
                            ['driver_gender', 'driver_age', 'victim_gender', 'victim_age'],
                            batch_size=batch_size
                        )
                accidents_to_update = []

                # Progress indicator
                self.stdout.write(f'Processed {idx:,} / {total_count:,} records...', ending='\r')

        # Save remaining records
        if accidents_to_update and not dry_run:
            with transaction.atomic():
                Accident.objects.bulk_update(
                    accidents_to_update,
                    ['driver_gender', 'driver_age', 'victim_gender', 'victim_age']
                )

        # Display results
        self.stdout.write('\n\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('EXTRACTION COMPLETE'))
        self.stdout.write('=' * 80)

        self.stdout.write(f'\nTotal records processed: {stats["total_processed"]:,}')
        self.stdout.write(f'\nDriver gender extracted: {stats["driver_gender_extracted"]:,}')
        self.stdout.write(f'  - Male drivers: {stats["male_drivers"]:,}')
        self.stdout.write(f'  - Female drivers: {stats["female_drivers"]:,}')
        self.stdout.write(f'\nVictim gender extracted: {stats["victim_gender_extracted"]:,}')
        self.stdout.write(f'  - Male victims: {stats["male_victims"]:,}')
        self.stdout.write(f'  - Female victims: {stats["female_victims"]:,}')
        self.stdout.write(f'\nDriver age extracted: {stats["driver_age_extracted"]:,}')
        self.stdout.write(f'Victim age extracted: {stats["victim_age_extracted"]:,}')

        if stats['male_drivers'] + stats['female_drivers'] > 0:
            male_pct = (stats['male_drivers'] / (stats['male_drivers'] + stats['female_drivers']) * 100)
            female_pct = (stats['female_drivers'] / (stats['male_drivers'] + stats['female_drivers']) * 100)
            self.stdout.write(f'\nDriver Gender Distribution:')
            self.stdout.write(f'  - Male: {male_pct:.1f}%')
            self.stdout.write(f'  - Female: {female_pct:.1f}%')

        # Phase 2: Fill remaining UNKNOWN records with statistical distribution
        fill_unknown = options.get('fill_unknown', False)
        if fill_unknown:
            self.stdout.write('\n' + '-' * 80)
            self.stdout.write(self.style.WARNING('PHASE 2: Filling UNKNOWN gender with statistical distribution'))
            self.stdout.write('-' * 80)
            self.stdout.write('Based on Philippine traffic accident statistics:')
            self.stdout.write('  Drivers: ~87% Male, ~13% Female (PNP/MMDA data)')
            self.stdout.write('  Victims: ~72% Male, ~28% Female (WHO Philippines data)\n')

            # Use a fixed seed for reproducibility
            rng = random.Random(42)

            # Driver gender: ~87% male
            MALE_DRIVER_RATIO = 0.87

            # Victim gender: ~72% male
            MALE_VICTIM_RATIO = 0.72

            unknown_accidents = Accident.objects.filter(driver_gender='UNKNOWN')
            unknown_count = unknown_accidents.count()
            self.stdout.write(f'Records with UNKNOWN driver_gender: {unknown_count:,}')

            unknown_victim = Accident.objects.filter(victim_gender='UNKNOWN')
            unknown_victim_count = unknown_victim.count()
            self.stdout.write(f'Records with UNKNOWN victim_gender: {unknown_victim_count:,}\n')

            fill_batch = []
            fill_stats = {'male_drivers': 0, 'female_drivers': 0, 'male_victims': 0, 'female_victims': 0}

            from django.db.models import Q
            for idx, acc in enumerate(Accident.objects.filter(
                Q(driver_gender='UNKNOWN') | Q(victim_gender='UNKNOWN')
            ).iterator(), 1):
                updated = False

                if acc.driver_gender == 'UNKNOWN':
                    acc.driver_gender = 'MALE' if rng.random() < MALE_DRIVER_RATIO else 'FEMALE'
                    fill_stats['male_drivers' if acc.driver_gender == 'MALE' else 'female_drivers'] += 1
                    updated = True

                if acc.victim_gender == 'UNKNOWN':
                    acc.victim_gender = 'MALE' if rng.random() < MALE_VICTIM_RATIO else 'FEMALE'
                    fill_stats['male_victims' if acc.victim_gender == 'MALE' else 'female_victims'] += 1
                    updated = True

                if updated:
                    fill_batch.append(acc)

                if len(fill_batch) >= batch_size:
                    if not dry_run:
                        with transaction.atomic():
                            Accident.objects.bulk_update(
                                fill_batch,
                                ['driver_gender', 'victim_gender'],
                                batch_size=batch_size
                            )
                    fill_batch = []
                    self.stdout.write(f'Filled {idx:,} records...', ending='\r')

            if fill_batch and not dry_run:
                with transaction.atomic():
                    Accident.objects.bulk_update(
                        fill_batch,
                        ['driver_gender', 'victim_gender'],
                        batch_size=batch_size
                    )

            total_filled = fill_stats['male_drivers'] + fill_stats['female_drivers']
            total_victims_filled = fill_stats['male_victims'] + fill_stats['female_victims']
            self.stdout.write(f'\n\nFilled driver gender for {total_filled:,} records:')
            self.stdout.write(f'  - Male: {fill_stats["male_drivers"]:,} ({fill_stats["male_drivers"]/max(total_filled,1)*100:.1f}%)')
            self.stdout.write(f'  - Female: {fill_stats["female_drivers"]:,} ({fill_stats["female_drivers"]/max(total_filled,1)*100:.1f}%)')
            self.stdout.write(f'\nFilled victim gender for {total_victims_filled:,} records:')
            self.stdout.write(f'  - Male: {fill_stats["male_victims"]:,} ({fill_stats["male_victims"]/max(total_victims_filled,1)*100:.1f}%)')
            self.stdout.write(f'  - Female: {fill_stats["female_victims"]:,} ({fill_stats["female_victims"]/max(total_victims_filled,1)*100:.1f}%)')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes were saved to the database.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nAll changes have been saved to the database.'))

        self.stdout.write('=' * 80 + '\n')

    def extract_person_data(self, text):
        """
        Extract gender and age from text format: (Age/Gender/Status/Nationality/Occupation)
        Example: "John Doe (25/Male/Injured/FILIPINO/DRIVER)"

        Returns: (gender, age)
        """
        if not text or text == 'nan':
            return None, None

        # Pattern: (age/gender/status/...)
        # Match first occurrence (primary person)
        pattern = r'\((\d+)/(Male|Female|male|female)'
        match = re.search(pattern, str(text))

        if match:
            age = int(match.group(1))
            gender = match.group(2).upper()
            return gender, age

        return None, None
