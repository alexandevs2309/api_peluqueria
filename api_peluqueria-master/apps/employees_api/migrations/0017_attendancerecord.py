from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0016_alter_employee_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendanceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('work_date', models.DateField()),
                ('check_in_at', models.DateTimeField(blank=True, null=True)),
                ('check_out_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('present', 'Present'), ('late', 'Late'), ('absent', 'Absent')], default='present', max_length=10)),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='employees_api.employee')),
            ],
            options={
                'ordering': ['-work_date', '-check_in_at'],
            },
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['employee', 'work_date'], name='employees_a_employe_e9f98d_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['status'], name='employees_a_status_f2353a_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='attendancerecord',
            unique_together={('employee', 'work_date')},
        ),
    ]
