from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accidents', '0028_systemsetting'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='pref_accident_view',
            field=models.CharField(blank=True, choices=[('', 'System Default'), ('cards', 'Cards'), ('table', 'Table')], default='', max_length=10, verbose_name='Accident page view'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='pref_hotspot_view',
            field=models.CharField(blank=True, choices=[('', 'System Default'), ('grid', 'Grid'), ('list', 'List')], default='', max_length=10, verbose_name='Hotspot page view'),
        ),
    ]
