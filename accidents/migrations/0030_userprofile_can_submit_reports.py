from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accidents', '0029_userprofile_display_prefs'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='can_submit_reports',
            field=models.BooleanField(default=True, help_text='Allow this user to access the report submission page', verbose_name='Can Submit Reports'),
        ),
    ]
