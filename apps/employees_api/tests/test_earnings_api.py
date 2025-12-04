import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, datetime
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from apps.employees_api.utils import date_to_year_fortnight

User = get_user_model()

class EarningsAPIFallbackTestCase(TestCase):
    """
    Test cases for earnings API fallback functionality.
    Tests that frequency + reference_date parameters are accepted and converted
    to year/fortnight internally while maintaining backward compatibility.
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Barbershop",
            subdomain="test",
            is_active=True
        )
        
        # Create user
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            full_name="Test User",
            tenant=self.tenant,
            role="manager"
        )
        
        # Create employee
        self.employee = Employee.objects.create(
            user=self.user,
            tenant=self.tenant,
            specialty="Corte",
            salary_type="commission",
            commission_percentage=40.0,
            is_active=True
        )
        
        # Create fortnight summary for testing
        self.fortnight_summary = FortnightSummary.objects.create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=24,  # December 2nd fortnight
            total_earnings=500.0,
            total_services=5,
            is_paid=False
        )
        
        # Authenticate client
        self.client.force_authenticate(user=self.user)
    
    def test_date_to_year_fortnight_helper(self):
        """Test the date_to_year_fortnight utility function"""
        # Test first fortnight of December 2024
        year, fortnight = date_to_year_fortnight("2024-12-04")
        self.assertEqual(year, 2024)
        self.assertEqual(fortnight, 23)  # December 1st fortnight
        
        # Test second fortnight of December 2024
        year, fortnight = date_to_year_fortnight("2024-12-20")
        self.assertEqual(year, 2024)
        self.assertEqual(fortnight, 24)  # December 2nd fortnight
        
        # Test with Date object
        year, fortnight = date_to_year_fortnight(date(2024, 12, 4))
        self.assertEqual(year, 2024)
        self.assertEqual(fortnight, 23)
        
        # Test invalid date format
        with self.assertRaises(ValueError) as cm:
            date_to_year_fortnight("invalid-date")
        self.assertIn("Invalid reference_date format", str(cm.exception))
    
    def test_get_my_earnings_with_year_fortnight_preserved(self):
        """Test that existing year/fortnight parameters still work"""
        url = reverse('earning-list')
        response = self.client.get(url, {
            'year': 2024,
            'fortnight': 24
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('employees', response.data)
        self.assertIn('summary', response.data)
        self.assertEqual(response.data['summary']['year'], 2024)
        self.assertEqual(response.data['summary']['fortnight'], 24)
    
    def test_get_my_earnings_with_frequency_reference_date_fallback(self):
        """Test that frequency + reference_date are accepted and converted"""
        url = reverse('earning-list')
        response = self.client.get(url, {
            'frequency': 'fortnightly',
            'reference_date': '2024-12-20'  # Should convert to year=2024, fortnight=24
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('employees', response.data)
        self.assertIn('summary', response.data)
        self.assertEqual(response.data['summary']['year'], 2024)
        self.assertEqual(response.data['summary']['fortnight'], 24)
    
    def test_post_pay_with_frequency_reference_date_fallback(self):
        """Test that pay endpoint accepts frequency + reference_date"""
        url = reverse('earning-pay')
        payload = {
            'employee_id': self.employee.id,
            'frequency': 'fortnightly',
            'reference_date': '2024-12-20',  # Should convert to year=2024, fortnight=24
            'payment_method': 'cash',
            'payment_reference': 'TEST-001',
            'payment_notes': 'Test payment'
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'paid')
        self.assertIn('summary', response.data)
        self.assertEqual(response.data['summary']['year'], 2024)
        self.assertEqual(response.data['summary']['fortnight'], 24)
        
        # Verify the payment was processed
        self.fortnight_summary.refresh_from_db()
        self.assertTrue(self.fortnight_summary.is_paid)
    
    def test_bad_reference_date_returns_400(self):
        """Test that invalid reference_date returns 400 error"""
        url = reverse('earning-list')
        response = self.client.get(url, {
            'frequency': 'fortnightly',
            'reference_date': 'bad-date'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Invalid reference_date format', response.data['error'])
    
    def test_unsupported_frequency_returns_400(self):
        """Test that unsupported frequency returns 400 error"""
        url = reverse('earning-list')
        response = self.client.get(url, {
            'frequency': 'monthly',
            'reference_date': '2024-12-04'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Unsupported frequency: monthly', response.data['error'])
    
    def test_pay_with_bad_reference_date_returns_400(self):
        """Test that pay endpoint returns 400 for invalid reference_date"""
        url = reverse('earning-pay')
        payload = {
            'employee_id': self.employee.id,
            'frequency': 'fortnightly',
            'reference_date': 'invalid-date',
            'payment_method': 'cash'
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Invalid reference_date format', response.data['error'])
    
    def test_pay_with_unsupported_frequency_returns_400(self):
        """Test that pay endpoint returns 400 for unsupported frequency"""
        url = reverse('earning-pay')
        payload = {
            'employee_id': self.employee.id,
            'frequency': 'weekly',
            'reference_date': '2024-12-04',
            'payment_method': 'cash'
        }
        
        response = self.client.post(url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Unsupported frequency: weekly', response.data['error'])
    
    def test_fallback_produces_same_result_as_year_fortnight(self):
        """Test that fallback produces exactly the same result as year/fortnight"""
        url = reverse('earning-list')
        
        # Request with year/fortnight
        response1 = self.client.get(url, {
            'year': 2024,
            'fortnight': 24
        })
        
        # Request with frequency/reference_date that should convert to same values
        response2 = self.client.get(url, {
            'frequency': 'fortnightly',
            'reference_date': '2024-12-20'  # Should convert to year=2024, fortnight=24
        })
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Both responses should have the same structure and values
        self.assertEqual(response1.data['summary']['year'], response2.data['summary']['year'])
        self.assertEqual(response1.data['summary']['fortnight'], response2.data['summary']['fortnight'])
        self.assertEqual(len(response1.data['employees']), len(response2.data['employees']))
    
    def test_missing_parameters_uses_current_fortnight(self):
        """Test that missing parameters defaults to current fortnight"""
        url = reverse('earning-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('employees', response.data)
        self.assertIn('summary', response.data)
        # Should have year and fortnight from current date
        self.assertIn('year', response.data['summary'])
        self.assertIn('fortnight', response.data['summary'])