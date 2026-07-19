import { Component, inject, computed } from '@angular/core';
import { BarbershopSettingsService } from '../services/barbershop-settings.service';

@Component({
  selector: 'app-business-hours',
  standalone: true,
  imports: [],
  template: `
    <div class="bg-white rounded-lg p-4 shadow-sm">
      <h3 class="font-semibold mb-3 flex items-center gap-2">
        <i class="pi pi-clock text-blue-600"></i>
        Horarios de Atención
      </h3>
      <div class="space-y-2">
        @for (day of daysWithHours(); track day.key) {
          <div class="flex justify-between text-sm">
            <span class="font-medium">{{ day.label }}</span>
            <span [class]="day.closed ? 'text-red-500' : 'text-green-600'">
              {{ day.closed ? 'Cerrado' : day.open + ' - ' + day.close }}
            </span>
          </div>
        }
      </div>
    </div>
  `
})
export class BusinessHoursComponent {
  private settingsService = inject(BarbershopSettingsService);

  days = [
    { key: 'monday', label: 'Lunes' },
    { key: 'tuesday', label: 'Martes' },
    { key: 'wednesday', label: 'Miércoles' },
    { key: 'thursday', label: 'Jueves' },
    { key: 'friday', label: 'Viernes' },
    { key: 'saturday', label: 'Sábado' },
    { key: 'sunday', label: 'Domingo' }
  ];

  daysWithHours = computed(() => {
    const settings = this.settingsService.settings();
    return this.days.map(day => {
      const hours = settings.business_hours[day.key] || { open: '08:00', close: '18:00', closed: false };
      return {
        ...day,
        ...hours
      };
    });
  });
}