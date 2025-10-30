from django.core.management.base import BaseCommand
import pandas as pd
from accidents.models import Accident
from datetime import datetime
from decimal import Decimal, InvalidOperation
import numpy as np

class Command(BaseCommand):
    help = 'Import accidents from CSV file with robust error handling'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records to import per batch (default: 500)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        batch_size = options['batch_size']
        
        self.stdout.write(self.style.WARNING('=' * 80))
        self.stdout.write(self.style.WARNING('ENHANCED ACCIDENT IMPORT SYSTEM'))
        self.stdout.write(self.style.WARNING('Handles missing values, large datasets, and data validation'))
        self.stdout.write(self.style.WARNING('=' * 80))
        
        try:
            # Read CSV with pandas - handle different encodings
            self.stdout.write('📂 Reading CSV file...')
            try:
                df = pd.read_csv(csv_file, encoding='cp1252')
            except:
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8')
                except:
                    df = pd.read_csv(csv_file, encoding='latin-1')
            
            total_rows = len(df)
            self.stdout.write(self.style.SUCCESS(f'✅ Found {total_rows} rows in CSV'))
            
            # Replace NaN with None for better handling
            df = df.replace({np.nan: None})
            
            imported = 0
            errors = 0
            skipped = 0
            error_log = []
            
            # Use bulk_create for better performance
            batch = []
            
            for index, row in df.iterrows():
                try:
                    # ==========================================
                    # SAFELY PARSE DATES WITH ERROR HANDLING
                    # ==========================================
                    date_reported = self.safe_parse_date(row.get('dateReported'))
                    date_committed = self.safe_parse_date(row.get('dateCommitted'))
                    
                    # 🆕 USE DEFAULT DATE IF MISSING (instead of skipping)
                    if not date_committed:
                        # Try to use year if available
                        year_value = self.safe_parse_int(row.get('Year'))
                        if year_value:
                            # Use January 1 of that year
                            date_committed = datetime(year_value, 1, 1).date()
                        else:
                            # Use a default date (e.g., 2020-01-01)
                            date_committed = datetime(2020, 1, 1).date()
                        error_log.append(f"Row {index + 2}: Missing dateCommitted - Using default date: {date_committed}")
                    
                    # ==========================================
                    # SAFELY PARSE COORDINATES WITH VALIDATION
                    # ==========================================
                    latitude = self.safe_parse_float(row.get('lat'))
                    longitude = self.safe_parse_float(row.get('lng'))
                    
                    # Validate coordinates (Caraga Region bounds)
                    # Caraga: lat 7.5-10.5, lng 124.5-127.0
                    if latitude and (latitude < 7.0 or latitude > 11.0):
                        latitude = None
                    if longitude and (longitude < 124.0 or longitude > 128.0):
                        longitude = None
                    
                    # 🆕 USE APPROXIMATE COORDINATES IF MISSING
                    if not latitude or not longitude:
                        # Get approximate coordinates based on location text
                        approx_coords = self.get_approximate_coordinates(
                            row.get('province'),
                            row.get('municipal'),
                            row.get('barangay')
                        )
                        
                        if approx_coords:
                            latitude, longitude = approx_coords
                            error_log.append(f"Row {index + 2}: Missing coordinates - Using approximate location for {row.get('municipal', 'UNKNOWN')}")
                        else:
                            # Last resort: Use Caraga Region center
                            latitude = 9.0  # Center of Caraga
                            longitude = 125.5
                            error_log.append(f"Row {index + 2}: Missing coordinates - Using Caraga Region center")
                    
                    # Now we NEVER skip - we always have date and coordinates!
                    
                    # ==========================================
                    # SAFELY PARSE TIME FIELDS
                    # ==========================================
                    time_reported = self.safe_parse_time(row.get('timeReported'))
                    time_committed = self.safe_parse_time(row.get('timeCommitted'))
                    
                    # ==========================================
                    # SAFELY PARSE NUMERIC FIELDS
                    # ==========================================
                    year = self.safe_parse_int(row.get('Year'))
                    victim_count = self.safe_parse_int(row.get('victimCount'), default=0)
                    suspect_count = self.safe_parse_int(row.get('suspectCount'), default=0)
                    
                    # ==========================================
                    # SAFELY PARSE BOOLEAN FIELDS
                    # ==========================================
                    victim_killed = self.safe_parse_boolean(row.get('victimKilled'))
                    victim_injured = self.safe_parse_boolean(row.get('victimInjured'))
                    victim_unharmed = self.safe_parse_boolean(row.get('victimUnharmed'))
                    
                    # ==========================================
                    # SAFELY GET STRING FIELDS WITH DEFAULTS
                    # ==========================================
                    province = self.safe_string(row.get('province'), 'UNKNOWN')
                    municipal = self.safe_string(row.get('municipal'), 'UNKNOWN')
                    barangay = self.safe_string(row.get('barangay'), 'UNKNOWN')
                    
                    # Create accident object
                    accident = Accident(
                        # Location fields
                        pro=self.safe_string(row.get('pro')),
                        ppo=self.safe_string(row.get('ppo')),
                        station=self.safe_string(row.get('stn')),
                        region=self.safe_string(row.get('region'), 'CARAGA'),
                        province=province,
                        municipal=municipal,
                        barangay=barangay,
                        street=self.safe_string(row.get('street')),
                        type_of_place=self.safe_string(row.get('typeofPlace')),
                        
                        # Coordinates
                        latitude=Decimal(str(latitude)),
                        longitude=Decimal(str(longitude)),
                        
                        # Date/Time fields
                        date_reported=date_reported,
                        time_reported=time_reported,
                        date_committed=date_committed,
                        time_committed=time_committed,
                        year=year,
                        
                        # Incident details
                        incident_type=self.safe_string(row.get('incidentType'), 'UNKNOWN'),
                        offense=self.safe_string(row.get('offense')),
                        offense_type=self.safe_string(row.get('offenseType')),
                        stage_of_felony=self.safe_string(row.get('stageoffelony')),
                        
                        # Victim/Suspect status
                        victim_killed=victim_killed,
                        victim_injured=victim_injured,
                        victim_unharmed=victim_unharmed,
                        victim_count=victim_count,
                        suspect_count=suspect_count,
                        
                        # Vehicle information
                        vehicle_kind=self.safe_string(row.get('vehicleKind')),
                        vehicle_make=self.safe_string(row.get('vehicleMake')),
                        vehicle_model=self.safe_string(row.get('vehicleModel')),
                        vehicle_plate_no=self.safe_string(row.get('vehiclePlateNo')),
                        
                        # Details
                        victim_details=self.safe_string(row.get('victim')),
                        suspect_details=self.safe_string(row.get('suspect')),
                        narrative=self.safe_string(row.get('narrative'), 'No details available'),
                        
                        # Case information
                        case_status=self.safe_string(row.get('casestatus'), 'UNKNOWN'),
                        case_solve_type=self.safe_string(row.get('caseSolveType')),
                    )
                    
                    batch.append(accident)
                    
                    # Bulk insert every batch_size records
                    if len(batch) >= batch_size:
                        Accident.objects.bulk_create(batch, ignore_conflicts=True)
                        imported += len(batch)
                        batch = []
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Imported {imported}/{total_rows} records...')
                        )
                        
                except Exception as e:
                    errors += 1
                    error_msg = f"Row {index + 2}: {str(e)}"
                    error_log.append(error_msg)
                    
                    # Print first 10 errors for debugging
                    if errors <= 10:
                        self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            
            # Insert remaining records
            if batch:
                Accident.objects.bulk_create(batch, ignore_conflicts=True)
                imported += len(batch)
            
            # ==========================================
            # FINAL SUMMARY REPORT
            # ==========================================
            self.stdout.write(self.style.WARNING('\n' + '=' * 80))
            self.stdout.write(self.style.WARNING('IMPORT SUMMARY'))
            self.stdout.write(self.style.WARNING('=' * 80))
            
            self.stdout.write(self.style.SUCCESS(f'✅ Successfully imported: {imported} records'))
            self.stdout.write(self.style.ERROR(f'❌ Errors encountered: {errors} records'))
            self.stdout.write(self.style.WARNING(f'⏭️  Skipped (missing data): {skipped} records'))
            self.stdout.write(f'📊 Total rows processed: {total_rows}')
            
            success_rate = (imported / total_rows * 100) if total_rows > 0 else 0
            self.stdout.write(self.style.SUCCESS(f'📈 Success Rate: {success_rate:.2f}%'))
            
            # Save error log to file if there are errors
            if error_log:
                error_file = 'import_errors.log'
                with open(error_file, 'w') as f:
                    f.write('\n'.join(error_log))
                self.stdout.write(
                    self.style.WARNING(f'\n⚠️  Error details saved to: {error_file}')
                )
            
            self.stdout.write(self.style.WARNING('=' * 80))
            
            if success_rate >= 95:
                self.stdout.write(self.style.SUCCESS('🎉 Import completed successfully!'))
            elif success_rate >= 80:
                self.stdout.write(self.style.WARNING('⚠️  Import completed with some issues'))
            else:
                self.stdout.write(self.style.ERROR('❌ Import completed with many errors'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'💥 Fatal error: {str(e)}'))
            raise
    
    # ==========================================
    # HELPER METHODS FOR SAFE DATA PARSING
    # ==========================================
    
    def safe_parse_date(self, value):
        """Safely parse date from various formats"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        try:
            # Try common date formats
            for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y']:
                try:
                    return datetime.strptime(str(value), fmt).date()
                except:
                    continue
            return None
        except:
            return None
    
    def safe_parse_time(self, value):
        """Safely parse time from various formats"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        try:
            # Clean the time string
            time_str = str(value).strip()
            
            # Try common time formats
            for fmt in ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']:
                try:
                    return datetime.strptime(time_str, fmt).time()
                except:
                    continue
            return None
        except:
            return None
    
    def safe_parse_float(self, value):
        """Safely parse float values"""
        if value is None or value == '':
            return None
        
        try:
            result = float(value)
            # Check if it's a valid number (not infinity or NaN)
            if np.isnan(result) or np.isinf(result):
                return None
            return result
        except (ValueError, TypeError, InvalidOperation):
            return None
    
    def safe_parse_int(self, value, default=None):
        """Safely parse integer values"""
        if value is None or value == '':
            return default
        
        try:
            return int(float(value))  # Convert through float first
        except (ValueError, TypeError):
            return default
    
    def safe_parse_boolean(self, value):
        """Safely parse boolean values"""
        if value is None:
            return False
        
        if isinstance(value, bool):
            return value
        
        value_str = str(value).strip().upper()
        return value_str in ['YES', 'TRUE', '1', 'Y', 'T']
    
    def safe_string(self, value, default=''):
        """Safely convert to string with default"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return default
        
        return str(value).strip()[:500]  # Limit length to avoid database errors
    
    def get_approximate_coordinates(self, province, municipal, barangay):
        """
        Get approximate coordinates based on location name
        Returns (latitude, longitude) tuple or None
        """
        # Approximate coordinates for major municipalities in Caraga Region
        # Format: 'PROVINCE|MUNICIPALITY': (lat, lng)
        location_coords = {
            # AGUSAN DEL NORTE
            'AGUSAN DEL NORTE|BUTUAN CITY': (8.9475, 125.5406),
            'AGUSAN DEL NORTE|CABADBARAN': (9.1231, 125.5347),
            'AGUSAN DEL NORTE|NASIPIT': (8.9897, 125.3456),
            'AGUSAN DEL NORTE|BUENAVISTA': (8.9731, 125.4064),
            'AGUSAN DEL NORTE|CARMEN': (9.0472, 125.6350),
            
            # AGUSAN DEL SUR
            'AGUSAN DEL SUR|SAN FRANCISCO': (8.5111, 125.9667),
            'AGUSAN DEL SUR|PROSPERIDAD': (8.6050, 125.9150),
            'AGUSAN DEL SUR|BUNAWAN': (8.1731, 125.9933),
            'AGUSAN DEL SUR|TRENTO': (8.0431, 126.0589),
            'AGUSAN DEL SUR|ROSARIO': (8.7850, 125.9358),
            'AGUSAN DEL SUR|TALACOGON': (8.6450, 125.7867),
            
            # SURIGAO DEL NORTE
            'SURIGAO DEL NORTE|SURIGAO CITY': (9.7856, 125.4919),
            'SURIGAO DEL NORTE|MAINIT': (9.5389, 125.5358),
            'SURIGAO DEL NORTE|ALEGRIA': (9.7347, 125.6089),
            'SURIGAO DEL NORTE|PLACER': (9.6656, 125.5986),
            'SURIGAO DEL NORTE|DAPA': (9.7592, 126.0517),
            
            # SURIGAO DEL SUR
            'SURIGAO DEL SUR|TANDAG': (9.0781, 126.1981),
            'SURIGAO DEL SUR|BISLIG': (8.2158, 126.3222),
            'SURIGAO DEL SUR|BAROBO': (8.5608, 126.2056),
            'SURIGAO DEL SUR|HINATUAN': (8.3736, 126.3378),
            'SURIGAO DEL SUR|LINGIG': (8.0417, 126.3833),
            
            # DINAGAT ISLANDS
            'DINAGAT ISLANDS|SAN JOSE': (10.0619, 125.5731),
            'DINAGAT ISLANDS|BASILISA': (10.1450, 125.5167),
            'DINAGAT ISLANDS|DINAGAT': (10.1289, 125.5944),
            'DINAGAT ISLANDS|LIBJO': (10.2239, 125.5361),
            'DINAGAT ISLANDS|LORETO': (10.0083, 125.5500),
        }
        
        # Try exact match first (Province|Municipality)
        if province and municipal:
            key = f"{province.upper().strip()}|{municipal.upper().strip()}"
            if key in location_coords:
                return location_coords[key]
        
        # Try province center as fallback
        province_centers = {
            'AGUSAN DEL NORTE': (8.9475, 125.5406),  # Butuan area
            'AGUSAN DEL SUR': (8.5111, 125.9667),     # San Francisco area
            'SURIGAO DEL NORTE': (9.7856, 125.4919),  # Surigao City
            'SURIGAO DEL SUR': (9.0781, 126.1981),    # Tandag
            'DINAGAT ISLANDS': (10.1289, 125.5944),   # Dinagat center
        }
        
        if province:
            province_key = province.upper().strip()
            if province_key in province_centers:
                return province_centers[province_key]
        
        # No match found
        return None