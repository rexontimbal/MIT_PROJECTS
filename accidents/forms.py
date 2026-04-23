from django import forms
from .models import AccidentReport, DropdownOption
from django.core.validators import MinValueValidator, MaxValueValidator


def get_dynamic_choices(field_name):
    """Get choices from DropdownOption table, with empty default."""
    try:
        choices = DropdownOption.get_choices(field_name)
        if choices:
            return [('', '-- Select --')] + choices + [('OTHER', 'Other')]
    except Exception:
        pass
    # Fallback to model choices if DB not ready
    return []


class AccidentReportForm(forms.ModelForm):
    """Traffic Accident Report (TAR) form — PNP Caraga Region"""

    class Meta:
        model = AccidentReport
        fields = [
            # B. Basic Information
            'incident_date', 'incident_time',
            # C. Accident Details
            'incident_type', 'incident_type_other', 'type_of_place', 'type_of_place_other',
            'cause_of_accident', 'cause_of_accident_other',
            'weather_condition', 'light_condition', 'road_condition', 'road_character',
            # C. Location
            'province', 'municipal', 'barangay', 'street_address',
            'latitude', 'longitude',
            # C. Offense / Legal Classification
            'offense', 'offense_other', 'offense_type', 'offense_type_other',
            'stage_of_felony', 'stage_of_felony_other',
            # D. Persons — Victim details
            'victim_address', 'victim_work_address', 'hospital_taken_to',
            # D. Persons — Suspect / Driver details
            'driver_license_no', 'suspect_relation_to_victim', 'suspect_address',
            # E. Vehicle Information
            'vehicle_kind', 'vehicle_kind_other', 'vehicle_make', 'vehicle_make_other',
            'vehicle_model', 'vehicle_model_other', 'vehicle_plate_no', 'vehicle_chassis_no',
            'vehicle_colorum', 'vehicle_registered_owner', 'vehicle_or_cr_no',
            'drug_involved',
            # F. Narrative
            'incident_description',
            # G. Sketch
            'sketch_image',
            # H. Action Taken
            'action_taken',
        ]

        widgets = {
            # Incident Details
            'incident_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'incident_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'incident_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_incident_type'}),
            'incident_type_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify...'}),
            'type_of_place': forms.Select(attrs={'class': 'form-control', 'id': 'id_type_of_place'}),
            'type_of_place_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify...'}),
            # Offense / Legal Classification
            'offense': forms.Select(attrs={'class': 'form-control', 'id': 'id_offense'}),
            'offense_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify offense...'}),
            'offense_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_offense_type'}),
            'offense_type_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify offense type...'}),
            'stage_of_felony': forms.Select(attrs={'class': 'form-control', 'id': 'id_stage_of_felony'}),
            'stage_of_felony_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify...'}),
            # Location
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'Click on map',
                'readonly': 'readonly', 'step': '0.000001'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'Click on map',
                'readonly': 'readonly', 'step': '0.000001'
            }),
            'province': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', 'Select Province'),
                ('AGUSAN DEL NORTE', 'Agusan del Norte'),
                ('AGUSAN DEL SUR', 'Agusan del Sur'),
                ('SURIGAO DEL NORTE', 'Surigao del Norte'),
                ('SURIGAO DEL SUR', 'Surigao del Sur'),
                ('DINAGAT ISLANDS', 'Dinagat Islands'),
            ]),
            'municipal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Municipality/City'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Barangay name'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street name or landmark'}),
            # TAR Scene / Road Conditions
            'cause_of_accident': forms.Select(attrs={'class': 'form-control', 'id': 'id_cause_of_accident'}),
            'cause_of_accident_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify cause...'}),
            'weather_condition': forms.Select(attrs={'class': 'form-control'}),
            'light_condition': forms.Select(attrs={'class': 'form-control'}),
            'road_condition': forms.Select(attrs={'class': 'form-control'}),
            'road_character': forms.Select(attrs={'class': 'form-control'}),
            # Action Taken
            'action_taken': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Describe actions taken by the responding officer (e.g., traffic investigation conducted, evidence gathered, charges filed, etc.)...'
            }),
            # Vehicle Info
            'vehicle_kind': forms.Select(attrs={'class': 'form-control', 'id': 'id_vehicle_kind'}),
            'vehicle_kind_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify...'}),
            'vehicle_make': forms.Select(attrs={'class': 'form-control', 'id': 'id_vehicle_make'}, choices=[('', 'Select Vehicle Type first')]),
            'vehicle_make_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify brand...'}),
            'vehicle_model': forms.Select(attrs={'class': 'form-control', 'id': 'id_vehicle_model'}, choices=[('', 'Select Vehicle Make first')]),
            'vehicle_model_other': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Please specify model...'}),
            'vehicle_plate_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., ABC 1234'}),
            'vehicle_chassis_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MHKE8FF22PJK001562'}),
            'vehicle_colorum': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_vehicle_colorum'}),
            'drug_involved': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_drug_involved'}),
            # Victim Enhanced Details
            'victim_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Current address of victim'}),
            'victim_work_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Work address of victim'}),
            'hospital_taken_to': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hospital name'}),
            # Suspect / Driver Enhanced Details
            'driver_license_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Driver's license number"}),
            'suspect_relation_to_victim': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Relation to victim'}),
            'suspect_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Current address of suspect'}),
            # Vehicle Enhanced Details
            'vehicle_registered_owner': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registered owner name'}),
            'vehicle_or_cr_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'OR/CR Number'}),
            # Sketch
            'sketch_image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            # Narrative
            'incident_description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Provide a detailed narrative of the accident including sequence of events, circumstances, and relevant details...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override choices with dynamic DB options (exclude 'OTHER' from DB, we add it manually)
        dynamic_fields = ['incident_type', 'type_of_place', 'offense', 'offense_type', 'stage_of_felony', 'vehicle_kind']
        for field_name in dynamic_fields:
            choices = get_dynamic_choices(field_name)
            if choices:
                # Remove duplicate OTHER if it's already in the DB choices
                seen_other = False
                cleaned = []
                for val, lbl in choices:
                    if val == 'OTHER':
                        if not seen_other:
                            cleaned.append((val, lbl))
                            seen_other = True
                    else:
                        cleaned.append((val, lbl))
                self.fields[field_name].choices = cleaned

    def clean_sketch_image(self):
        sketch = self.cleaned_data.get('sketch_image')
        if sketch and hasattr(sketch, 'content_type'):
            allowed = ['image/jpeg', 'image/png', 'image/jpg']
            if sketch.content_type not in allowed:
                raise forms.ValidationError('Only image files (JPG, PNG) are allowed for sketch upload.')
            if sketch.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Sketch image must be under 5MB.')
        return sketch

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        if latitude and longitude:
            if not (7.5 <= float(latitude) <= 10.5 and 124.5 <= float(longitude) <= 127.0):
                raise forms.ValidationError('Coordinates must be within Caraga Region bounds')
        return cleaned_data


class AccidentFilterForm(forms.Form):
    """Form for filtering accidents in list view"""
    
    province = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    municipal = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    year = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_hotspot = forms.BooleanField(
        required=False,
        label='Show only hotspot accidents',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        from .models import Accident
        
        # Populate province choices
        provinces = Accident.objects.values_list('province', flat=True).distinct()
        self.fields['province'].choices = [('', 'All Provinces')] + [
            (p, p) for p in provinces
        ]
        
        # Populate municipal choices
        municipalities = Accident.objects.values_list('municipal', flat=True).distinct()
        self.fields['municipal'].choices = [('', 'All Municipalities')] + [
            (m, m) for m in municipalities
        ]
        
        # Populate year choices
        years = Accident.objects.values_list('year', flat=True).distinct().order_by('-year')
        self.fields['year'].choices = [('', 'All Years')] + [
            (y, y) for y in years
        ]


class ClusteringJobForm(forms.Form):
    """Form for running AGNES clustering"""
    
    linkage_method = forms.ChoiceField(
        choices=[
            ('complete', 'Complete Linkage'),
            ('single', 'Single Linkage'),
            ('average', 'Average Linkage'),
        ],
        initial='complete',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Method for calculating distance between clusters'
    )
    
    distance_threshold = forms.FloatField(
        initial=0.05,
        min_value=0.01,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01'
        }),
        help_text='Maximum distance to merge clusters (in decimal degrees, ~0.05 = 5km)'
    )
    
    min_cluster_size = forms.IntegerField(
        initial=3,
        min_value=2,
        max_value=20,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Minimum number of accidents to form a hotspot'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='Start date for analysis (leave empty for all data)'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text='End date for analysis (leave empty for all data)'
    )