from django import forms
from .models import AccidentReport
from django.core.validators import MinValueValidator, MaxValueValidator

class AccidentReportForm(forms.ModelForm):
    """Form for reporting new accidents - matches CARAGA dataset structure"""

    class Meta:
        model = AccidentReport
        fields = [
            'incident_date', 'incident_time', 'incident_type', 'incident_type_other', 'type_of_place', 'type_of_place_other',
            'offense', 'offense_other', 'offense_type', 'offense_type_other', 'stage_of_felony',
            'latitude', 'longitude', 'province', 'municipal', 'barangay', 'street_address',
            'vehicle_kind', 'vehicle_kind_other', 'vehicle_make', 'vehicle_make_other', 'vehicle_model', 'vehicle_model_other', 'vehicle_plate_no', 'vehicle_chassis_no', 'vehicle_colorum',
            'drug_involved',
            'incident_description',
            'photo_1', 'photo_2', 'photo_3',
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
            'stage_of_felony': forms.Select(attrs={'class': 'form-control'}),
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
            # Narrative
            'incident_description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Provide a detailed narrative of the accident including sequence of events, circumstances, and relevant details...'
            }),
            # Photos
            'photo_1': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'photo_2': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'photo_3': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

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