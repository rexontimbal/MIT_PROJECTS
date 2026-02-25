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


class Command(BaseCommand):
    help = 'Extract gender and age data from existing accident records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to database',
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
