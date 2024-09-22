from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('faculty', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='borrowrequest',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
