# Migration: Add parent_value to DropdownOption, vehicle_make/model to FIELD_CHOICES,
# stage_of_felony_other to AccidentReport

from django.db import migrations, models


def seed_vehicle_data(apps, schema_editor):
    """Seed vehicle make and model options into DropdownOption table."""
    DropdownOption = apps.get_model('accidents', 'DropdownOption')

    vehicle_data = {
        'MOTORCYCLE': {
            'YAMAHA': ('Yamaha', ['Mio', 'NMAX', 'Aerox', 'Sniper', 'YTX', 'XTZ', 'MT-15', 'R15', 'FZ-i', 'Sight']),
            'HONDA': ('Honda', ['Click', 'Beat', 'PCX', 'ADV', 'Wave', 'XRM', 'TMX', 'CRF', 'CBR', 'Rebel']),
            'SUZUKI': ('Suzuki', ['Raider', 'Skydrive', 'Smash', 'Gixxer', 'Burgman', 'GSX']),
            'KAWASAKI': ('Kawasaki', ['Barako', 'CT100', 'Rouser', 'Ninja', 'Z400', 'Dominar', 'KLX']),
            'RUSI': ('Rusi', ['Classic', 'Sigma', 'Rapid', 'Flash', 'DL150']),
        },
        'TRICYCLE': {
            'YAMAHA': ('Yamaha', ['Mio', 'NMAX', 'Sniper', 'YTX']),
            'HONDA': ('Honda', ['TMX', 'Wave', 'XRM', 'Click']),
            'SUZUKI': ('Suzuki', ['Raider', 'Smash']),
            'KAWASAKI': ('Kawasaki', ['Barako', 'CT100', 'Rouser']),
            'RUSI': ('Rusi', ['Classic', 'Sigma', 'Rapid']),
        },
        'CAR': {
            'TOYOTA': ('Toyota', ['Vios', 'Wigo', 'Raize', 'Camry', 'Corolla Altis', 'GR Yaris', 'Corolla Cross']),
            'MITSUBISHI': ('Mitsubishi', ['Mirage', 'Mirage G4', 'Lancer', 'Attrage']),
            'HONDA': ('Honda', ['City', 'Civic', 'Accord', 'Brio']),
            'HYUNDAI': ('Hyundai', ['Accent', 'Elantra', 'Reina', 'Ioniq']),
            'NISSAN': ('Nissan', ['Almera', 'Sylphy', 'GT-R']),
            'KIA': ('Kia', ['Sonet', 'Stonic', 'Forte', 'K3']),
            'SUZUKI': ('Suzuki', ['Ciaz', 'Dzire', 'Swift', 'Celerio', 'S-Presso', 'Alto']),
            'MAZDA': ('Mazda', ['3', '6', 'MX-5']),
            'BMW': ('BMW', ['3 Series', '5 Series', 'X1']),
            'MERCEDES': ('Mercedes-Benz', ['A-Class', 'C-Class', 'E-Class']),
            'SUBARU': ('Subaru', ['Impreza', 'WRX', 'BRZ']),
            'VOLKSWAGEN': ('Volkswagen', ['Lavida', 'Lamando']),
            'BYD': ('BYD', ['Dolphin', 'Seal', 'Han']),
            'GEELY': ('Geely', ['Emgrand', 'Coolray Sedan']),
            'CHERY': ('Chery', ['Arrizo 5', 'Arrizo 8']),
            'MG': ('MG', ['5', 'GT']),
            'CHEVROLET': ('Chevrolet', ['Sail', 'Malibu']),
        },
        'SUV': {
            'TOYOTA': ('Toyota', ['Fortuner', 'Hilux', 'Innova', 'Rush', 'Land Cruiser', 'RAV4', 'Avanza']),
            'MITSUBISHI': ('Mitsubishi', ['Xpander', 'Xpander Cross', 'Montero Sport', 'Strada', 'Outlander']),
            'FORD': ('Ford', ['Ranger', 'Everest', 'Territory', 'Explorer', 'Raptor']),
            'NISSAN': ('Nissan', ['Navara', 'Terra', 'X-Trail', 'Patrol']),
            'HONDA': ('Honda', ['CR-V', 'HR-V', 'BR-V', 'ZR-V']),
            'HYUNDAI': ('Hyundai', ['Tucson', 'Creta', 'Santa Fe', 'Stargazer', 'Palisade']),
            'KIA': ('Kia', ['Seltos', 'Sportage', 'Sorento', 'Carnival']),
            'ISUZU': ('Isuzu', ['D-Max', 'mu-X']),
            'SUZUKI': ('Suzuki', ['Ertiga', 'XL7', 'Vitara', 'Jimny', 'Grand Vitara']),
            'MAZDA': ('Mazda', ['CX-5', 'CX-30', 'CX-3', 'CX-9', 'BT-50']),
            'SUBARU': ('Subaru', ['Forester', 'XV', 'Outback', 'Evoltis']),
            'BMW': ('BMW', ['X1', 'X3', 'X5']),
            'MERCEDES': ('Mercedes-Benz', ['GLA', 'GLC', 'GLE']),
            'BYD': ('BYD', ['Atto 3', 'Tang', 'Song Plus']),
            'GEELY': ('Geely', ['Coolray', 'Azkarra', 'Okavango', 'Monjaro']),
            'CHERY': ('Chery', ['Tiggo 4 Pro', 'Tiggo 7 Pro', 'Tiggo 8 Pro']),
            'MG': ('MG', ['ZS', 'HS', 'RX5', 'Extender']),
            'GAC': ('GAC', ['GS3', 'GS4', 'GS8', 'Emkoo']),
            'CHANGAN': ('Changan', ['CS35 Plus', 'CS55 Plus', 'CS75 Plus', 'UNI-T']),
            'VOLKSWAGEN': ('Volkswagen', ['T-Cross', 'Tiguan']),
            'CHEVROLET': ('Chevrolet', ['Tracker', 'Trailblazer', 'Colorado']),
        },
        'VAN': {
            'TOYOTA': ('Toyota', ['HiAce', 'Lite Ace', 'Grandia', 'Super Grandia']),
            'NISSAN': ('Nissan', ['NV350 Urvan']),
            'HYUNDAI': ('Hyundai', ['Staria', 'Grand Starex', 'Stargazer X']),
            'KIA': ('Kia', ['Carnival']),
            'FOTON': ('Foton', ['Transvan', 'View Traveller', 'Toano']),
            'GAC': ('GAC', ['GN8']),
        },
        'TRUCK': {
            'ISUZU': ('Isuzu', ['NLR', 'NMR', 'NPR', 'FRR', 'FVR', 'CYZ', 'EXZ']),
            'HINO': ('Hino', ['300 Series', '500 Series', '700 Series']),
            'FOTON': ('Foton', ['Tornado', 'Hurricane', 'EST-M']),
            'HYUNDAI': ('Hyundai', ['HD36', 'HD65', 'Mighty']),
            'MITSUBISHI': ('Mitsubishi', ['Canter', 'Fighter']),
        },
        'BUS': {
            'HINO': ('Hino', ['RK Series', 'RM Series']),
            'ISUZU': ('Isuzu', ['LT Series']),
            'HYUNDAI': ('Hyundai', ['County', 'Universe']),
        },
    }

    for kind_value, makes in vehicle_data.items():
        for i, (make_value, (make_label, model_list)) in enumerate(makes.items()):
            DropdownOption.objects.get_or_create(
                field_name='vehicle_make',
                value=make_value,
                parent_value=kind_value,
                defaults={
                    'label': make_label,
                    'sort_order': i * 10,
                    'is_default': True,
                    'is_active': True,
                }
            )
            parent_key = f'{kind_value}__{make_value}'
            for j, model_name in enumerate(model_list):
                DropdownOption.objects.get_or_create(
                    field_name='vehicle_model',
                    value=model_name,
                    parent_value=parent_key,
                    defaults={
                        'label': model_name,
                        'sort_order': j * 10,
                        'is_default': True,
                        'is_active': True,
                    }
                )


class Migration(migrations.Migration):

    dependencies = [
        ('accidents', '0035_add_dropdown_options_and_edit_permission'),
    ]

    operations = [
        # Add parent_value field to DropdownOption
        migrations.AddField(
            model_name='dropdownoption',
            name='parent_value',
            field=models.CharField(blank=True, default='', help_text='Parent option value for hierarchical fields', max_length=300),
        ),
        # Update unique_together to include parent_value
        migrations.AlterUniqueTogether(
            name='dropdownoption',
            unique_together={('field_name', 'value', 'parent_value')},
        ),
        # Update field_name choices to include vehicle_make and vehicle_model
        migrations.AlterField(
            model_name='dropdownoption',
            name='field_name',
            field=models.CharField(
                choices=[
                    ('incident_type', 'Incident Type'),
                    ('type_of_place', 'Type of Place'),
                    ('offense', 'Offense'),
                    ('offense_type', 'Offense Type'),
                    ('stage_of_felony', 'Stage of Felony'),
                    ('vehicle_kind', 'Vehicle Type'),
                    ('vehicle_make', 'Vehicle Make / Brand'),
                    ('vehicle_model', 'Vehicle Model'),
                ],
                db_index=True, max_length=50
            ),
        ),
        # Add stage_of_felony_other to AccidentReport
        migrations.AddField(
            model_name='accidentreport',
            name='stage_of_felony_other',
            field=models.CharField(blank=True, help_text='Specify if Other is selected', max_length=200, null=True),
        ),
        # Seed vehicle make/model data
        migrations.RunPython(seed_vehicle_data, migrations.RunPython.noop),
    ]
