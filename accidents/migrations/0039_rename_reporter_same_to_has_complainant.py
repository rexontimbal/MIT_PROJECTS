from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accidents', '0038_reporter_civilian_separation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='accidentreport',
            old_name='reporter_same_as_officer',
            new_name='has_complainant',
        ),
    ]
