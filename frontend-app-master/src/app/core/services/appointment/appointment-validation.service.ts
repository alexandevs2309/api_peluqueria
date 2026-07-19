import { Injectable } from '@angular/core';
import { AppointmentWithDetails } from '../appointment/appointment.service';

export interface ConflictValidation {
    hasConflict: boolean;
    message?: string;
    errorCode?: string;
    errorParams?: Record<string, string>;
    conflictingAppointment?: AppointmentWithDetails;
}

@Injectable({
    providedIn: 'root'
})
export class AppointmentValidationService {

    /**
     * Valida si hay conflicto de horario para un empleado
     */
    validateStylistAvailability(
        stylistId: number,
        startTime: Date,
        duration: number,
        existingAppointments: AppointmentWithDetails[],
        excludeAppointmentId?: number
    ): ConflictValidation {
        const endTime = new Date(startTime.getTime() + duration * 60000);

        // Filtrar citas del mismo empleado en el mismo día
        const stylistAppointments = existingAppointments.filter(apt => 
            apt.stylist === stylistId &&
            apt.status === 'scheduled' &&
            apt.id !== excludeAppointmentId &&
            this.isSameDay(new Date(apt.date_time), startTime)
        );

        // Verificar conflictos
        for (const apt of stylistAppointments) {
            const aptStart = new Date(apt.date_time);
            const aptEnd = new Date(aptStart.getTime() + (apt.service_duration || 30) * 60000);

            // Hay conflicto si los rangos se solapan
            if (this.rangesOverlap(startTime, endTime, aptStart, aptEnd)) {
                return {
                    hasConflict: true,
                    message: `El empleado ya tiene una cita de ${aptStart.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} a ${aptEnd.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`,
                    errorCode: 'validation.employee_conflict',
                    errorParams: {
                        start: aptStart.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
                        end: aptEnd.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
                    },
                    conflictingAppointment: apt
                };
            }
        }

        return { hasConflict: false };
    }

    /**
     * Encuentra el próximo horario disponible para un empleado
     */
    findNextAvailableSlot(
        stylistId: number,
        preferredDate: Date,
        duration: number,
        existingAppointments: AppointmentWithDetails[],
        workingHours = { start: 8, end: 20 }
    ): Date | null {
        const date = new Date(preferredDate);
        date.setHours(workingHours.start, 0, 0, 0);

        while (date.getHours() < workingHours.end) {
            const validation = this.validateStylistAvailability(
                stylistId,
                date,
                duration,
                existingAppointments
            );

            if (!validation.hasConflict) {
                return new Date(date);
            }

            // Avanzar 15 minutos
            date.setMinutes(date.getMinutes() + 15);
        }

        return null;
    }

    /**
     * Calcula tiempo de espera estimado
     */
    calculateWaitTime(
        stylistId: number,
        existingAppointments: AppointmentWithDetails[]
    ): number {
        const now = new Date();
        const today = existingAppointments.filter(apt =>
            apt.stylist === stylistId &&
            apt.status === 'scheduled' &&
            this.isSameDay(new Date(apt.date_time), now)
        );

        if (today.length === 0) return 0;

        // Encontrar la última cita del día
        const lastAppointment = today.reduce((latest, current) => {
            const currentTime = new Date(current.date_time);
            const latestTime = new Date(latest.date_time);
            return currentTime > latestTime ? current : latest;
        });

        const lastEnd = new Date(lastAppointment.date_time);
        lastEnd.setMinutes(lastEnd.getMinutes() + (lastAppointment.service_duration || 30));

        // Si la última cita ya pasó, no hay espera
        if (lastEnd < now) return 0;

        // Calcular minutos de espera
        return Math.ceil((lastEnd.getTime() - now.getTime()) / 60000);
    }

    /**
     * Valida si un cliente ya tiene cita en ese horario
     */
    validateClientAvailability(
        clientId: number,
        startTime: Date,
        existingAppointments: AppointmentWithDetails[],
        excludeAppointmentId?: number
    ): ConflictValidation {
        const clientAppointments = existingAppointments.filter(apt =>
            apt.client === clientId &&
            apt.status === 'scheduled' &&
            apt.id !== excludeAppointmentId &&
            this.isSameDay(new Date(apt.date_time), startTime)
        );

        for (const apt of clientAppointments) {
            const aptTime = new Date(apt.date_time);
            const timeDiff = Math.abs(startTime.getTime() - aptTime.getTime()) / 60000;

            // Si hay otra cita del mismo cliente en menos de 1 hora
            if (timeDiff < 60) {
                return {
                    hasConflict: true,
                    message: `El cliente ya tiene una cita a las ${aptTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}`,
                    errorCode: 'validation.client_conflict',
                    errorParams: {
                        time: aptTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
                    },
                    conflictingAppointment: apt
                };
            }
        }

        return { hasConflict: false };
    }

    private rangesOverlap(start1: Date, end1: Date, start2: Date, end2: Date): boolean {
        return start1 < end2 && end1 > start2;
    }

    private isSameDay(date1: Date, date2: Date): boolean {
        return date1.toDateString() === date2.toDateString();
    }
}
