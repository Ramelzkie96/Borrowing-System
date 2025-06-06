# Generated by Django 5.1.4 on 2025-04-26 14:42

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservationUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('student_id', models.CharField(max_length=9, unique=True)),
                ('year_level', models.CharField(choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year')], max_length=10)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('course', models.CharField(max_length=50)),
                ('phone_number', models.CharField(max_length=15)),
                ('password', models.CharField(max_length=128)),
                ('profile_image', models.ImageField(default='profile_pics/users.jpg', upload_to='profile_pics/')),
            ],
        ),
        migrations.CreateModel(
            name='StudentReservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_id', models.CharField(max_length=20)),
                ('name', models.CharField(max_length=100)),
                ('course', models.CharField(max_length=50)),
                ('year_level', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(max_length=15)),
                ('reserve_date', models.CharField(max_length=50)),
                ('date_return', models.CharField(max_length=50, null=True)),
                ('purpose', models.TextField(null=True)),
                ('status', models.CharField(default='Pending', max_length=20)),
                ('upload_image', models.ImageField(blank=True, null=True, upload_to='borrow_upload/')),
                ('is_borrow', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reservation.reservationuser')),
            ],
        ),
        migrations.CreateModel(
            name='ReservationItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=100)),
                ('description', models.TextField(default='N/A')),
                ('quantity', models.PositiveIntegerField()),
                ('status', models.CharField(max_length=50, null=True)),
                ('notification', models.CharField(max_length=500, null=True)),
                ('handled_by', models.CharField(blank=True, max_length=50, null=True)),
                ('handled_by_profile_picture', models.URLField(blank=True, max_length=500, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('is_handled', models.BooleanField(default=False)),
                ('user_type', models.CharField(blank=True, max_length=50, null=True)),
                ('is_update', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('handle_status', models.CharField(default='Pending', max_length=15)),
                ('user_facultyItem', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reservation.reservationuser')),
                ('reservation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='reservation.studentreservation')),
            ],
        ),
    ]
