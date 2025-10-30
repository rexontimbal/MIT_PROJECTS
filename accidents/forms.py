from django import forms
from .models import AccidentReport
from django.core.validators import MinValueValidator, MaxValueValidator

class AccidentReportForm(forms.ModelForm):
    """Form for reporting new accidents"""
    
    # Additional fields for better UX
    vehicle_type_1 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Motorcycle, Car, Truck'
        })
    )
    vehicle_plate_1 = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., ABC 1234'
        })
    )
    
    vehicle_type_2 = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Second vehicle (if any)'
        })
    )
    vehicle_plate_2 = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Plate number'
        })
    )
    
    class Meta:
        model = AccidentReport
        fields = [
            'reporter_name',
            'reporter_contact',
            'incident_date',
            'incident_time',
            'latitude',
            'longitude',
            'province',
            'municipal',
            'barangay',
            'street_address',
            'incident_description',
            'casualties_killed',
            'casualties_injured',
            'photo_1',
            'photo_2',
            'photo_3',
        ]
        
        widgets = {
            'reporter_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name'
            }),
            'reporter_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number or email'
            }),
            'incident_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'incident_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Click on map to set location',
                'readonly': 'readonly',
                'step': '0.000001'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Click on map to set location',
                'readonly': 'readonly',
                'step': '0.000001'
            }),
            'province': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('', 'Select Province'),
                ('AGUSAN DEL NORTE', 'Agusan del Norte'),
                ('AGUSAN DEL SUR', 'Agusan del Sur'),
                ('SURIGAO DEL NORTE', 'Surigao del Norte'),
                ('SURIGAO DEL SUR', 'Surigao del Sur'),
                ('DINAGAT ISLANDS', 'Dinagat Islands'),
            ]),
            'municipal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Municipality/City'
            }),
            'barangay': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Barangay name'
            }),
            'street_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Street name or landmark'
            }),
            'incident_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Describe what happened in detail...'
            }),
            'casualties_killed': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '0'
            }),
            'casualties_injured': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'value': '0'
            }),
            'photo_1': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'photo_2': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'photo_3': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate coordinates
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if latitude and longitude:
            # Check if coordinates are within Caraga Region
            if not (7.5 <= float(latitude) <= 10.5 and 124.5 <= float(longitude) <= 127.0):
                raise forms.ValidationError(
                    'Coordinates must be within Caraga Region bounds'
                )
        
        # Validate casualties
        killed = cleaned_data.get('casualties_killed', 0)
        injured = cleaned_data.get('casualties_injured', 0)
        
        if killed < 0 or injured < 0:
            raise forms.ValidationError('Casualties cannot be negative')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Build vehicles_involved JSON from individual vehicle fields
        vehicles = []
        
        vehicle_type_1 = self.cleaned_data.get('vehicle_type_1')
        vehicle_plate_1 = self.cleaned_data.get('vehicle_plate_1')
        if vehicle_type_1:
            vehicles.append({
                'type': vehicle_type_1,
                'plate': vehicle_plate_1 or 'N/A'
            })
        
        vehicle_type_2 = self.cleaned_data.get('vehicle_type_2')
        vehicle_plate_2 = self.cleaned_data.get('vehicle_plate_2')
        if vehicle_type_2:
            vehicles.append({
                'type': vehicle_type_2,
                'plate': vehicle_plate_2 or 'N/A'
            })
        
        instance.vehicles_involved = vehicles
        
        if commit:
            instance.save()
        
        return instance


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